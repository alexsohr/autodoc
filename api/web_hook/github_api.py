import os
import json
import hmac
import re
import logging
import ssl
import aiohttp
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple
from fastapi import HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from api.web_hook.github_models import GithubPushEvent
from fastapi import FastAPI
import websockets
from fastapi.middleware.cors import CORSMiddleware
from api.web_hook.github_models import WikiStructure
from api.web_hook.github_prompts import generate_wiki_page_prompt
import asyncio

# Import the FastAPI app instance
from api.web_hook.github_prompts import generate_wiki_structure_prompt

from dotenv import load_dotenv
from api.data_pipeline import DatabaseManager
from api.web_hook.github_api_herlpers import parse_wiki_pages_from_xml, parse_wiki_sections_from_xml

load_dotenv()

app = FastAPI(
    title="Github Wehook API",
    description="API for webhooks"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Configure logger
logger = logging.getLogger(__name__)

def extract_wiki_structure_xml(wiki_structure_response, logger=None):
    """
    Clean up the AI response and extract the <wiki_structure>...</wiki_structure> XML block.
    Raises ValueError if the response is empty or no valid XML is found.
    """
    if not wiki_structure_response or str(wiki_structure_response).strip() == "":
        if logger:
            logger.error("Wiki structure response is empty - this indicates an issue with the model call")
        raise ValueError("Wiki structure response is empty")

    wiki_structure_response = str(wiki_structure_response)
    wiki_structure_response = re.sub(r'^```(?:xml)?\s*', '', wiki_structure_response, flags=re.IGNORECASE)
    wiki_structure_response = re.sub(r'```\s*$', '', wiki_structure_response, flags=re.IGNORECASE)
    match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", wiki_structure_response, re.MULTILINE)

    if not match:
        if logger:
            logger.error(f"No valid XML structure found in AI response. Response length: {len(wiki_structure_response)}")
            logger.error(f"First 500 chars of response: {wiki_structure_response[:500]}")
        raise ValueError("No valid XML structure found in AI response")

    xmlMatch = match.group(0)
    xmlText = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xmlMatch)
    return xmlText

async def generate_wiki_structure(owner: str, repo: str, file_tree: str, readme: str) -> str:
    """
    Generate the wiki structure XML using an LLM or stub.
    Parameters:
        owner (str): Repository owner
        repo (str): Repository name
        file_tree (str): File tree as string
        readme (str): README content
    Returns:
        str: XML string representing the wiki structure
    """
    # For now, simulate LLM response for testing
    # In production, call the LLM API here
    return f"""
<wiki_structure>
  <title>{repo} Wiki</title>
  <description>Auto-generated wiki for {owner}/{repo}</description>
  <pages>
    <page id=\"page-1\">
      <title>Overview</title>
      <description>Project overview</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>README.md</file_path>
      </relevant_files>
      <related_pages></related_pages>
    </page>
    <page id=\"page-2\">
      <title>Architecture</title>
      <description>System architecture</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>src/main.py</file_path>
      </relevant_files>
      <related_pages></related_pages>
    </page>
  </pages>
</wiki_structure>
"""
 

def parse_wiki_structure(xml_text: str) -> Tuple[str, str, List[dict]]:
    """
    Parse the XML wiki structure and extract title, description, and pages.
    Parameters:
        xml_text (str): XML string
    Returns:
        Tuple[str, str, List[dict]]: (title, description, pages)
    """
    root = ET.fromstring(xml_text)
    title = root.findtext('title', default='')
    description = root.findtext('description', default='')
    pages = []
    for page_el in root.findall('.//page'):
        page = {
            'id': page_el.get('id', ''),
            'title': page_el.findtext('title', default=''),
            'description': page_el.findtext('description', default=''),
            'importance': page_el.findtext('importance', default='medium'),
            'file_paths': [fp.text for fp in page_el.findall('.//file_path') if fp.text],
            'related_pages': [rel.text for rel in page_el.findall('.//related') if rel.text],
        }
        pages.append(page)
    return title, description, pages

MAX_RETRIES = 3

async def generate_page_content(
    page: Dict,
    owner: str,
    repo: str,
    repo_url: str, # Object/Dictionary with owner, repo, type, etc.
    generated_pages = {}, # Dictionary to hold generated content
) -> Dict:
    page_id = page['id']
    page_title = page['title']
    file_paths = page['filePaths']

    try:
        # --- Input Validation ---
        if not owner or not repo:
            raise ValueError('Invalid repository information. Owner and repo name are required.')

        # Update generated_pages with a placeholder
        generated_pages[page_id] = {**page, 'content': 'Loading...'}

        # --- Prompt Construction ---
        # This part translates directly using Python f-strings or .format()
        file_list_markdown = '\n'.join([f"- [{path}]({path})" for path in file_paths])
        prompt_content = generate_wiki_page_prompt(page_title, file_list_markdown, file_paths)

        # --- Prepare Request Body ---
        request_body = {
            'repo_url': repo_url,
            'type': 'github',
            'messages': [{
                'role': 'user',
                'content': prompt_content
            }],
            'language': 'English'
        }

        content = ''
        last_error = None

        # --- Retry Logic ---
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"Attempt {attempt}/{MAX_RETRIES} for page: {page_title}")
            content = '' # Reset content for each attempt

            try:
                # --- WebSocket Attempt ---
                # Need to determine the server base URL in Python context
                server_base_url = 'http://localhost:8001' # Example
                ws_base_url = server_base_url.replace('http', 'ws')
                ws_url = f"{ws_base_url}/ws/chat"

                try:
                    async with websockets.connect(ws_url) as websocket:
                        logger.info(f"WebSocket connection established for page: {page_title} (attempt {attempt})")
                        await websocket.send(json.dumps(request_body))

                        # Receive messages
                        # Collect all response chunks
                        async for message in websocket:
                            try:
                                content += message
                            except asyncio.TimeoutError:
                                logger.warning(f"WebSocket read timeout for page: {page_title}")
                                break
                            except Exception as e:
                                logger.error(f"WebSocket receive error for page {page_title}: {e}")
                                raise e # Re-raise to trigger fallback

                        logger.info(f"WebSocket response complete. Total length: {len(content)}")
                    logger.info(f"WebSocket connection closed for page: {page_title} (attempt {attempt})")
                    # If we reach here, WebSocket was successful (at least connection and initial send)
                    # The content variable holds the received data.
                    if content: # Check if any content was received
                         logger.info(f"Successfully generated content for {page_title} via WebSocket on attempt {attempt}, length: {len(content)} characters")
                         break # Exit retry loop on success

                except Exception as ws_error:
                    logger.error(f"WebSocket error on attempt {attempt}, falling back to HTTP: {ws_error}")

            except Exception as err:
                last_error = err
                logger.error(f"Attempt {attempt}/{MAX_RETRIES} failed for page {page_id}: {err}")

                # If this is not the last attempt, wait
                if attempt < MAX_RETRIES:
                    wait_time = attempt * 1 # Progressive backoff: 1s, 2s, 3s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

        # --- Check if all retries failed ---
        if not content and last_error:
            raise last_error

        # --- Clean up markdown delimiters ---
        content = content.strip() # Remove leading/trailing whitespace
        if content.lower().startswith('```markdown'):
             content = content[len('```markdown'):].lstrip()
        if content.lower().endswith('```'):
             content = content[:-len('```')].rstrip()


        # --- Store the FINAL generated content (Simulated) ---
        updated_page = {**page, 'content': content}
        generated_pages[page_id] = updated_page
        return generated_pages

    except Exception as err:
        logger.error(f"Error generating content for page {page_id} after {MAX_RETRIES} attempts: {err}")
        error_message = str(err) if isinstance(err, Exception) else 'Unknown error'
        # Update page state to show error (Simulated)
        generated_pages[page_id] = {**page, 'content': f"Error generating content after {MAX_RETRIES} retries: {error_message}"}
        # Set global error state (Simulated)
        # set_error(f"Failed to generate content for {page_title} after {MAX_RETRIES} retries.")
        # Resolve even on error to unblock queue (Simulated)
        # This might involve signaling completion for this specific page task.
 

async def process_github_repository_async(github_event: GithubPushEvent, actor_name: str = None):
    """
    Process a Github repository asynchronously to generate wiki documentation and content.
    Parameters:
        github_event (GithubpushEvent): Github push event information
        actor_name (str, optional): Name of the user who triggered the webhook
    Returns:
        dict: Result containing wiki structure and generated pages
    """
    try:
        repo_url = github_event.repository.html_url
        logger.info(f"Processing Github repository: {repo_url}")
        repo_parts = github_event.repository.full_name.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid repository full_name format: {github_event.repository.full_name}")
            return
        owner, repo = repo_parts

        # Create the repository structure
        database_manager = DatabaseManager()
        database_manager._create_repo(repo_url, "github")
        repo_location = database_manager.repo_paths["save_repo_dir"]
        logger.info(f"Saved the repo at {repo_location}")

        # Fetch file tree and README - fetchRepositoryUrl
        file_tree = await get_repo_file_tree(owner, repo, github_event.repository.default_branch)
        readme_content = await get_repo_readme(owner, repo)
        logger.info(f"First 100 chars of README for {owner}/{repo}: {readme_content[:100]}")
        
        logger.info(f"Starting async wiki generation for Github repository: {owner}/{repo}")
        # Use the generate_github_wiki_structure_prompt function to generate the request body
        repo_url = f"https://github.org/{owner}/{repo}"
        # Prepare request body for wiki structure generation
        

        # Create request body for WebSocket
        request_body = {
            "repo_url": repo_url,
            "type": "github",
            "messages": [{
                "role": "user",
                "content": generate_wiki_structure_prompt(
                    owner=owner,
                    repo=repo,
                    file_tree=file_tree,
                    readme_content=readme_content
                )
            }]
        }

        # WebSocket URL (assuming the server is running on localhost:8001)
        ws_url = "ws://localhost:8001/ws/chat"

        wiki_structure_response = ""

        try:
            # Connect to WebSocket and get response
            async with websockets.connect(ws_url) as websocket:
                logger.info("WebSocket connection established for wiki structure generation")

                # Send the request as JSON
                await websocket.send(json.dumps(request_body))
                logger.info("Sent request to WebSocket")

                # Collect all response chunks
                async for message in websocket:
                    wiki_structure_response += message
                    logger.debug(f"Received chunk: {len(message)} characters")

                logger.info(f"WebSocket response complete. Total length: {len(wiki_structure_response)}")

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")

        logger.info(f"Wiki structure response length: {len(wiki_structure_response)}")
        logger.info(f"Wiki structure response: {wiki_structure_response}")


        # Extract the XML structure from the response
        xmlText = extract_wiki_structure_xml(wiki_structure_response, logger=logger)
        
        root = ET.fromstring(xmlText)
        title_el = root.find('title')
        description_el = root.find('description')
        pages_els = root.findall('.//page')
        title = title_el.text if title_el is not None else ''
        description = description_el.text if description_el is not None else ''
        logger.info(f"The number of pages are {len(pages_els)}")

        # TODO: Add retry ability
        pages = parse_wiki_pages_from_xml(pages_els)
        logger.info(f"Number of pages: {len(pages)}")
        
        sections_els = root.findall('.//section')
        sections, root_sections = parse_wiki_sections_from_xml(sections_els)
        logger.info(f"Number of root sections: {len(root_sections)}")
        logger.info(f"Root sections: {root_sections}")
        logger.info(f"Number of sections: {len(sections)}")
        logger.info(f"Sections: {sections}")

        # Generate wiki structure XML
        wiki_structure_xml = WikiStructure

        # Mark all pages as in progress (simulate with a set)
        pages_in_progress = set(page['id'] for page in pages)
        logger.info(f"Starting generation for {len(pages)} pages sequentially")
        generated_pages = {}

        for page in pages:
            try:
                generated_pages = await generate_page_content(page=page, owner=owner, repo=repo, repo_url=repo_url, 
                    generated_pages=generated_pages)
            finally:
                pages_in_progress.discard(page['id'])

        logger.info(f"All pages processed. {generated_pages}")


        # title, description, pages = parse_wiki_structure(wiki_structure_xml)
        # logger.info(f"Parsed wiki structure: {len(pages)} pages")
        # # Generate content for each page
        # generated_pages = {}
        # for page in pages:
        #     content = await generate_page_content(page, owner, repo)
        #     generated_pages[page['id']] = {
        #         'id': page['id'],
        #         'title': page['title'],
        #         'content': content,
        #         'file_paths': page['file_paths'],
        #         'importance': page['importance'],
        #         'related_pages': page['related_pages'],
        #     }
        # Compose result
        result = {
            'wiki_structure': {
                'title': title,
                'description': description,
                'pages': pages
            },
            'generated_pages': "generated_pages",
            'repo_url': repo_url
        }
        logger.info(f"Wiki generation complete for {owner}/{repo}")
        return result
    except Exception as e:
        logger.error(f"Error processing Github repository {github_event.repository.full_name}: {str(e)}", exc_info=True)
        return {'error': str(e)}
 

async def get_repo_file_tree(owner: str, repo: str, default_branch: str) -> str:
    """
    Get the file tree of a Github repository.
    Args:
        owner (str): Repository owner
        repo (str): Repository name
        default_branch (str): Default branch name
    Returns:
        str: File tree as a string with one file per line
    """
    try:
        # Get GitHub API token from environment
        token = os.environ.get("GITHUB_API_TOKEN", "")

        # Create headers for GitHub API
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'

        # Try to get the tree data for common branch names, starting with default_branch
        branches_to_try = [default_branch] if default_branch else []
        # Remove duplicates while preserving order
        branches_to_try = list(dict.fromkeys(branches_to_try))

        tree_data = None
        api_error_details = ''

        # Create SSL context that handles certificate verification issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            for branch in branches_to_try:
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
                logger.info(f"Fetching repository structure from branch: {branch}")

                try:
                    async with session.get(api_url, headers=headers) as response:
                        if response.status == 200:
                            tree_data = await response.json()
                            logger.info('Successfully fetched repository structure')
                            break
                        else:
                            error_data = await response.text()
                            api_error_details = f"Status: {response.status}, Response: {error_data}"
                            logger.error(f"Error fetching repository structure: {api_error_details}")
                except Exception as err:
                    logger.error(f"Network error fetching branch {branch}: {err}")
                    continue

        if not tree_data or 'tree' not in tree_data:
            if api_error_details:
                logger.error(f"Could not fetch repository structure. API Error: {api_error_details}")
                return ""
            else:
                logger.error('Could not fetch repository structure. Repository might not exist, be empty or private.')
                return ""

        # Convert tree data to a string representation (filter for files only)
        file_tree = tree_data['tree']
        file_paths = [
            item['path'] for item in file_tree
            if item.get('type') == 'blob'  # 'blob' represents files, 'tree' represents directories
        ]

        file_tree_string = '\n'.join(file_paths)
        logger.info(f"Successfully generated file tree with {len(file_paths)} files")
        return file_tree_string

    except Exception as e:
        logger.error(f"Error getting file tree for {owner}/{repo}: {str(e)}", exc_info=True)
        return ""
 

async def get_repo_readme(owner: str, repo: str) -> str:
    """
    Get the README content of a Github repository.
    Args:
        owner (str): Repository owner
        repo (str): Repository name
    Returns:
        str: README content as a string
    """
    try:
        # Get Github API token from environment
        token = os.environ.get("GITHUB_API_TOKEN", "")
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Create SSL context that handles certificate verification issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Try GitHub API first
            api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    readme_data = await response.json()
                    # GitHub API returns base64 encoded content
                    import base64
                    return base64.b64decode(readme_data['content']).decode('utf-8')
            # If no README found, return empty string
            logger.warning(f"No README found for repository {owner}/{repo}")
            return ""
    except Exception as e:
        logger.error(f"Error getting README for {owner}/{repo}: {str(e)}", exc_info=True)
        return ""
 

def clone_repo(self, params=None, method='GET', data=None, endpoint=''):
    """
    Make a request to the Github API.
    Args:
        params (dict, optional): Query parameters for the request
        method (str): HTTP method ('GET' or 'POST')
        data (dict, optional): Data to send in the request body (for POST requests)
        endpoint (str): API endpoint to call (e.g., 'repositories/{owner}/{repo}/src')
    Returns:
        dict: JSON response from the Github API
    Raises:
        HTTPError: If the request fails
    """
    url = f"https://github.org/{endpoint}"
    if method == 'GET':
        response = requests.get(url, auth=(self.inputs.sid, self.inputs.password), params=params)
    elif method == 'POST':
        response = requests.post(url, auth=(self.inputs.sid, self.inputs.password), json=data)
    response.raise_for_status()
    return response.json()
 

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for GitHub issue events. This will be the dedicated entry point for GitHub issue events.
    It immediately returns a 202 Accepted response and starts the generation process in the background.
    Args:
        request: The incoming request containing the GitHub webhook payload
        background_tasks: FastAPI's BackgroundTasks for async processing
    Returns:
        A 202 Accepted response indicating the webhook was received and processing has started
    """
    try:
        # Parse the webhook payload
        payload = await request.json()
        # Extract GitHub event type from headers
        github_event = request.headers.get("X-GitHub-Event")
        logger.info(f"Received GitHub webhook event: {github_event}")
        logger.info(f"Request headers: {request.headers}")
        # Log the event
        action = payload.get("action", None)
        logger.info(f"Received GitHub webhook event with action: {action}")
        # Validate HMAC-SHA256 signature
        signature = request.headers.get("X-Hub-Signature")
        if not signature:
            logger.error("Missing HMAC-SHA256 signature in webhook headers")
            raise HTTPException(status_code=400, detail="Missing HMAC-SHA256 signature")
        # secret = os.environ.get("Github_WEBHOOK_SECRET", "")
        # if not secret:
        #     logger.error("Webhook secret not configured in environment variables")
        #     raise HTTPException(status_code=500, detail="Webhook secret not configured")
        # computed_signature = hmac.new(secret.encode(), await request.body(), hashlib.sha256).hexdigest()
        # if not hmac.compare_digest(computed_signature, signature):
        #     logger.error("Invalid HMAC-SHA256 signature")
        #     raise HTTPException(status_code=403, detail="Invalid HMAC-SHA256 signature")
        # Check if this is a GitHub issue event
        if action == "closed" and github_event == "push":
            try:
                # Parse the issue event data
                push_event = GithubPushEvent(**payload)
                logger.info(f"Push event is {push_event}")
                logger.info(f"Processing GitHub push event: {action} for push #{push_event.number}")

                # Add the background task for processing
                background_tasks.add_task(
                    process_github_repository_async,
                    github_event=push_event
                )
                logger.info(f"Background task added for processing repository: {push_event.repository.full_name}")
                return JSONResponse(
                    status_code=202,
                    content={"message": f"Webhook received. Processing repository {push_event.repository.full_name} in background."}
                )
            except Exception as e:
                logger.error(f"Error parsing GitHub issue event: {str(e)}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Invalid issue event format: {str(e)}")
        else:
            # For other event types, just acknowledge receipt
            logger.info(f"Received unsupported GitHub event with action: {action}")
            return JSONResponse(
                status_code=202,
                content={"message": "Webhook received, but event type is not supported for processing."}
            )
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON in webhook payload")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or use default
    webhook_port = int(os.environ.get("WEBHOOK_PORT", 8002))

    logger.info(f"Starting GitHub Webhook API on port {webhook_port}")

    # Run the webhook FastAPI app with uvicorn
    uvicorn.run(
        "api.web_hook.github_api:app",
        host="0.0.0.0",
        port=webhook_port,
        reload=True  # Webhooks should be stable, no hot reload needed
    )
