import os
import json
import hmac
import re
import logging
import aiohttp
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple
from fastapi import HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from api.web_hook.github_models import GithubPushEvent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the FastAPI app instance
from api.web_hook.github_prompts import generate_wiki_structure_prompt
from api.websocket_wiki import handle_websocket_chat
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Streaming API",
    description="API for streaming chat completions"
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
 

async def generate_page_content(page: dict, owner: str, repo: str) -> str:
    """
    Generate content for a wiki page (stub/LLM call).
    Parameters:
        page (dict): Page info
        owner (str): Repository owner
        repo (str): Repository name
    Returns:
        str: Markdown content for the page
    """
    # Simulate content generation
    return f"# {page['title']}\n\nThis is the auto-generated content for {page['title']} in {owner}/{repo}.\n\nSources: {', '.join(page['file_paths'])}"
 

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
        repo_url = f"https://github.org/{github_event.repository.full_name}"
        repo_parts = github_event.repository.full_name.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid repository full_name format: {github_event.repository.full_name}")
            return
        owner, repo = repo_parts
        logger.info(f"Starting async wiki generation for Github repository: {owner}/{repo}")
        # Fetch file tree and README - fetchRepositoryUrl
        file_tree = await get_repo_file_tree(owner, repo)
        readme_content = await get_repo_readme(owner, repo)
        logger.info(f"Fetched file tree and README for {owner}/{repo}")
        # Use the generate_github_wiki_structure_prompt function to generate the request body
        repo_url = f"https://github.org/{owner}/{repo}"
        # Prepare request body for wiki structure generation
        request_body = {
            "repo_url": repo_url, 
            "type": "bitbucket",
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
        response = await handle_websocket_chat(
            request_body=request_body,
        )
        response = re.sub(r'^```(?:xml)?\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*$', '', response, flags=re.IGNORECASE)
        match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", response, re.MULTILINE)
        xmlMatch = match.group(0) if match else None
        xmlText = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xmlMatch)
        # xml_text is your XML string
        root = ET.fromstring(xmlText)
        title_el = root.find('title')
        description_el = root.find('description')
        pages_els = root.findall('.//page')
        title = title_el.text if title_el is not None else ''
        description = description_el.text if description_el is not None else ''
        pages = []
        # TODO: Add retyr ability
        for page_el in pages_els:
            id_ = page_el.get('id', f'page-{len(pages) + 1}')
            title_el = page_el.find('title')
            importance_el = page_el.find('importance')
            file_path_els = page_el.findall('file_path')
            related_els = page_el.findall('related')
            title = title_el.text if title_el is not None else ''
            importance = 'medium'
            if importance_el is not None:
                if importance_el.text == 'high':
                    importance = 'high'
                elif importance_el.text == 'medium':
                    importance = 'medium'
                else:
                    importance = 'low'
            file_paths = [el.text for el in file_path_els if el.text]
            related_pages = [el.text for el in related_els if el.text]
            pages.append({
                'id': id_,
                'title': title,
                'content': '',  # Will be generated later
                'filePaths': file_paths,
                'importance': importance,
                'relatedPages': related_pages
            })
        sections = []
        root_sections = []
        sections_els = root.findall('.//section')
        if sections_els:
            for section_el in sections_els:
                id_ = section_el.get('id', f'section-{len(sections) + 1}')
                title_el = section_el.find('title')
                page_ref_els = section_el.findall('page_ref')
                section_ref_els = section_el.findall('section_ref')
                title = title_el.text if title_el is not None else ''
                pages = [el.text for el in page_ref_els if el.text]
                subsections = [el.text for el in section_ref_els if el.text]
                section = {
                    'id': id_,
                    'title': title,
                    'pages': pages,
                    'subsections': subsections if subsections else None
                }
                sections.append(section)
                # Check if this is a root section (not referenced by any other section)
                is_referenced = False
                for other_section in sections_els:
                    other_section_refs = other_section.findall('section_ref')
                    for ref in other_section_refs:
                        if ref.text == id_:
                            is_referenced = True
                if not is_referenced:
                    root_sections.append(id_)
        # Generate wiki structure XML
        wiki_structure_xml = await generate_wiki_structure(owner, repo, file_tree, readme_content)
        logger.info(f"Wiki structure XML generated for {owner}/{repo}")
        # Parse wiki structure
        title, description, pages = parse_wiki_structure(wiki_structure_xml)
        logger.info(f"Parsed wiki structure: {len(pages)} pages")
        # Generate content for each page
        generated_pages = {}
        for page in pages:
            content = await generate_page_content(page, owner, repo)
            generated_pages[page['id']] = {
                'id': page['id'],
                'title': page['title'],
                'content': content,
                'file_paths': page['file_paths'],
                'importance': page['importance'],
                'related_pages': page['related_pages'],
            }
        # Compose result
        result = {
            'wiki_structure': {
                'title': title,
                'description': description,
                'pages': pages
            },
            'generated_pages': generated_pages,
            'repo_url': repo_url
        }
        logger.info(f"Wiki generation complete for {owner}/{repo}")
        return result
    except Exception as e:
        logger.error(f"Error processing Github repository {github_event.repository.full_name}: {str(e)}", exc_info=True)
        return {'error': str(e)}
 

async def get_repo_file_tree(owner: str, repo: str) -> str:
    """
    Get the file tree of a Github repository.
    Args:
        owner (str): Repository owner
        repo (str): Repository name
    Returns:
        str: File tree as a string with one file per line
    """
    try:
        # Get Github API token from environment
        token = os.environ.get("GITHUB_API_TOKEN", "")
        # Build API URL
        api_url = f"https://api.github.org/2.0/repositories/{owner}/{repo}/src"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params={"recursive": "true"}) as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract file paths from the response
                    files = []
                    for file_info in data.get("values", []):
                        if file_info.get("type") == "commit_file":
                            files.append(file_info.get("path", ""))
                    return "\n".join(files)
                else:
                    logger.error(f"Failed to get repository file tree: {response.status}")
                    return "Error: Failed to fetch repository file tree"
    except Exception as e:
        logger.error(f"Error getting file tree for {owner}/{repo}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"
 

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
        # Build API URL - try common README filenames
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with aiohttp.ClientSession() as session:
            for readme_file in readme_files:
                api_url = f"https://api.github.org/2.0/repositories/{owner}/{repo}/src/master/{readme_file}"
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
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
 

@app.post("/webhook/github")
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
        logger.info(f"Received Github webhook payload: {json.dumps(payload, indent=2)}")
        # Log the event
        action = payload.get("action")
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
        if action == "closed":
            try:
                # Parse the issue event data
                push_event = GithubPushEvent(**payload)
                logger.info(f"Processing GitHub push event: {action} for push #{push_event.number}")

                # Add the background task for processing
                background_tasks.add_task(
                    process_github_repository_async,
                    github_event=push_event,
                    actor_name=push_event.sender.login
                )
                logger.info(f"Background task added for processing repository: {push_event.repository.full_name}")
                return JSONResponse(
                    status_code=202,
                    content={"message": f"Webhook received. Processing repository {push_event.repository.full_name} in background."}
                )
            except Exception as e:
                logger.error(f"Error parsing GitHub push event: {str(e)}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Invalid push event format: {str(e)}")
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

