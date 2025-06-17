import os
import json
import logging
import asyncio
import websockets
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from dotenv import load_dotenv

# Imports from other new modules
from api.web_hook.github_service import get_repo_file_tree, get_repo_readme
from api.web_hook.utils import extract_wiki_structure_xml, parse_wiki_structure, generate_llms_txt
# Imports from existing modules
# Updated to include WikiPageDetail and WikiSection for Pydantic model instantiation
from api.web_hook.github_models import GithubPushEvent, WikiStructure, WikiPageDetail, WikiSection
from api.web_hook.github_prompts import generate_wiki_structure_prompt, generate_wiki_page_prompt
from api.web_hook.github_api_helpers import parse_wiki_sections_from_xml # parse_wiki_pages_from_xml removed
# from api.data_pipeline import DatabaseManager # Commented out as per previous steps

load_dotenv()

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

MAX_RETRIES_PAGE_CONTENT = 3

async def generate_page_content(
    page: Dict,
    owner: str,
    repo: str,
    repo_url: str,
    generated_pages: Dict | None = None,
) -> Dict:
    page_id = page['id']
    page_title = page['title']
    file_paths = page.get('filePaths', [])

    if generated_pages is None:
        generated_pages = {}

    logger.info(f"Starting content generation for page: {page_title} (ID: {page_id}) for repo {owner}/{repo}")

    try:
        if not owner or not repo:
            raise ValueError('Invalid repository information. Owner and repo name are required.')

        generated_pages[page_id] = {**page, 'content': 'Loading...'}

        file_list_markdown = '\n'.join([f"- [{path}]({path})" for path in file_paths])
        prompt_content = generate_wiki_page_prompt(page_title, file_list_markdown, file_paths)

        request_body = {
            'repo_url': repo_url,
            'type': 'github',
            'messages': [{'role': 'user', 'content': prompt_content}],
            'language': 'English'
        }

        content = ''
        last_error = None
        ws_url = os.getenv("WS_API")
        if not ws_url:
            logger.error("WS_API environment variable not set. Cannot connect to WebSocket.")
            raise EnvironmentError("WS_API environment variable not set.")

        for attempt in range(1, MAX_RETRIES_PAGE_CONTENT + 1):
            logger.info(f"Content generation attempt {attempt}/{MAX_RETRIES_PAGE_CONTENT} for page: {page_title}")
            current_content_chunk = ''

            try:
                async with websockets.connect(ws_url) as websocket:
                    logger.debug(f"WebSocket conn established for page: {page_title} (attempt {attempt})")
                    await websocket.send(json.dumps(request_body))
                    logger.debug(f"Sent request to WebSocket for page: {page_title}")
                    async for message in websocket:
                        current_content_chunk += message
                    logger.debug(f"WebSocket response complete for {page_title}. Length: {len(current_content_chunk)}")

                if current_content_chunk:
                    content = current_content_chunk
                    logger.info(f"Success: content for {page_title} via WebSocket attempt {attempt}, length: {len(content)}")
                    break
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"WebSocket conn closed error for {page_title} attempt {attempt}: {e}", exc_info=True)
                last_error = e
            except Exception as ws_error:
                logger.error(f"WebSocket error on attempt {attempt} for {page_title}: {ws_error}", exc_info=True)
                last_error = ws_error

            if content:
                break

            if attempt < MAX_RETRIES_PAGE_CONTENT:
                wait_time = attempt * 2
                logger.info(f"Waiting {wait_time}s before retry for page {page_title}...")
                await asyncio.sleep(wait_time)

        if not content and last_error:
            logger.error(f"Failed to generate content for page {page_id} after {MAX_RETRIES_PAGE_CONTENT} attempts. Last error: {last_error}")
            raise last_error

        content = content.strip()
        if content.startswith('```markdown'):
            content = content[len('```markdown'):].lstrip()
        if content.endswith('```'):
            content = content[:-len('```')].rstrip()

        updated_page = {**page, 'content': content}
        generated_pages[page_id] = updated_page
        logger.info(f"Finished content generation for page: {page_title} (ID: {page_id})")
        return generated_pages

    except Exception as err:
        logger.error(f"Critical error in generate_page_content for page {page_id}: {err}", exc_info=True)
        error_message = str(err)
        generated_pages[page_id] = {**page, 'content': f"Error generating content: {error_message}"}
        return generated_pages


async def _fetch_repository_details(owner: str, repo_name: str, default_branch: str):
    logger.info(f"Fetching repository details for {owner}/{repo_name}, branch: {default_branch}")
    file_tree_str = await get_repo_file_tree(owner, repo_name, default_branch)
    if not file_tree_str:
        logger.warning(f"File tree is empty for {owner}/{repo_name}.")

    readme_content = await get_repo_readme(owner, repo_name)
    if not readme_content:
        logger.warning(f"README is empty for {owner}/{repo_name}.")
    return file_tree_str, readme_content


async def _generate_wiki_structure(owner: str, repo_name: str, file_tree_str: str, readme_content: str, repo_url: str):
    logger.info(f"Generating wiki structure for: {owner}/{repo_name}")

    wiki_structure_prompt_content = generate_wiki_structure_prompt(
        owner=owner,
        repo=repo_name,
        file_tree=file_tree_str,
        readme_content=readme_content
    )

    request_body_structure = {
        "repo_url": repo_url,
        "type": "github",
        "messages": [{"role": "user", "content": wiki_structure_prompt_content}]
    }

    ws_url = os.getenv("WS_API")
    if not ws_url:
        logger.error("WS_API environment variable not set for wiki structure generation.")
        raise EnvironmentError("WS_API environment variable not set for wiki structure generation.")

    wiki_structure_response_raw = ""
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info(f"WebSocket conn established for wiki structure: {owner}/{repo_name}")
            await websocket.send(json.dumps(request_body_structure))
            logger.debug(f"Sent wiki structure request to WebSocket for {owner}/{repo_name}")
            async for message in websocket:
                wiki_structure_response_raw += message
            logger.info(f"Wiki structure WebSocket response complete for {owner}/{repo_name}. Length: {len(wiki_structure_response_raw)}")
    except Exception as e:
        logger.error(f"WebSocket conn failed for wiki structure ({owner}/{repo_name}): {e}", exc_info=True)
        raise

    if not wiki_structure_response_raw.strip():
        logger.error(f"Received empty wiki structure response from LLM for {owner}/{repo_name}")
        raise ValueError("Received empty wiki structure response from LLM.")

    xml_text = extract_wiki_structure_xml(wiki_structure_response_raw, logger_instance=logger)

    parsed_title, parsed_description, parsed_pages_list = parse_wiki_structure(xml_text)
    logger.info(f"Parsed {len(parsed_pages_list)} pages from wiki structure for {owner}/{repo_name} using utils.parse_wiki_structure.")

    root = ET.fromstring(xml_text)
    sections_els = root.findall('.//section')
    parsed_sections, parsed_root_sections = parse_wiki_sections_from_xml(sections_els)
    logger.info(f"Parsed {len(parsed_sections)} sections and {len(parsed_root_sections)} root sections for {owner}/{repo_name}.")

    return parsed_title, parsed_description, parsed_pages_list, parsed_sections, parsed_root_sections


async def _generate_all_page_content(pages_list: List[Dict], owner: str, repo_name: str, repo_url: str):
    generated_pages_content = {}
    logger.info(f"Starting content generation for {len(pages_list)} pages for repo {owner}/{repo_name} sequentially.")

    for page_meta_data in pages_list:
        try:
            await generate_page_content(
                page=page_meta_data,
                owner=owner,
                repo=repo_name,
                repo_url=repo_url,
                generated_pages=generated_pages_content
            )
        except Exception as e_page_gen:
            logger.error(f"Error during content generation for page {page_meta_data.get('id')} in {owner}/{repo_name}: {e_page_gen}", exc_info=True)
            # Error is logged within generate_page_content, continue with other pages.

    logger.info(f"All page content generation tasks initiated for {owner}/{repo_name}. Check logs for individual page statuses.")
    return generated_pages_content


async def generate_wiki_for_repository(github_event: GithubPushEvent, actor_name: str = None):
    repo_full_name = github_event.repository.full_name
    repo_url = github_event.repository.html_url
    logger.info(f"Starting wiki generation for Github repository: {repo_full_name} ({repo_url}) triggered by {actor_name or 'unknown'}.")

    try:
        repo_parts = repo_full_name.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid repository full_name format: {repo_full_name}")
            raise ValueError(f"Invalid repository full_name format: {repo_full_name}")
        owner, repo_name = repo_parts

        # Step 1: Fetch repository details
        file_tree_str, readme_content = await _fetch_repository_details(owner, repo_name, github_event.repository.default_branch)

        # Step 2: Generate wiki structure (title, description, pages list, sections)
        title, description, pages_list, sections, root_sections = await _generate_wiki_structure(
            owner, repo_name, file_tree_str, readme_content, repo_url
        )

        # Step 3: Generate content for each page
        generated_pages_map = await _generate_all_page_content(pages_list, owner, repo_name, repo_url)

        # Step 4: Construct WikiStructure Pydantic model
        # Convert list of page dicts to list of WikiPageDetail models
        page_models = []
        for page_dict in pages_list:
            # page_dict is from parse_wiki_structure, keys: id, title, description, importance, file_paths, related_pages
            # These should match WikiPageDetail fields.
            # Content will be added later.
            page_models.append(WikiPageDetail(**page_dict, content="")) # Add empty content initially

        # Convert list of section dicts to list of WikiSection models
        section_models = [WikiSection(**sec_dict) for sec_dict in sections]

        wiki_model_instance = WikiStructure(
            id=f"wiki-{owner}-{repo_name}",
            title=title,
            description=description,
            pages=page_models,
            sections=section_models,
            root_sections=root_sections
        )

        # Update pages in wiki_model_instance with generated content
        # generated_pages_map has page_id -> {full page dict with content}
        for page_model in wiki_model_instance.pages:
            if page_model.id in generated_pages_map and 'content' in generated_pages_map[page_model.id]:
                page_model.content = generated_pages_map[page_model.id]['content']

        # Step 5: Generate llms.txt (or other outputs)
        llms_filename = f"{owner}_{repo_name}_llms.txt"
        # generate_llms_txt expects a map of page_id to page_data (including content)
        # generated_pages_map is suitable here as it contains the full page dicts with content.
        generate_llms_txt(generated_pages_map, filename=llms_filename)
        logger.info(f"Successfully generated {llms_filename} for {repo_full_name}")

        # TODO: export_wiki_python call will be re-evaluated later.
        # await export_wiki_python(wiki_model_instance, generated_pages_map, repo_name, repo_url)

        final_result = {
            # Use model_dump for Pydantic V2, or dict for V1
            'wiki_structure': wiki_model_instance.model_dump(exclude_none=True),
            'generated_pages': generated_pages_map,
            'repo_url': repo_url
        }
        logger.info(f"Wiki generation process complete for {repo_full_name}.")
        return final_result

    except EnvironmentError as env_err:
        logger.critical(f"Environment configuration error for {repo_full_name}: {env_err}", exc_info=True)
        return {'error': str(env_err), 'status': 'environment_error'}
    except ValueError as val_err:
        logger.error(f"Data validation error for {repo_full_name}: {val_err}", exc_info=True)
        return {'error': str(val_err), 'status': 'validation_error'}
    except websockets.exceptions.WebSocketException as ws_err:
        logger.error(f"A WebSocket error occurred during processing for {repo_full_name}: {ws_err}", exc_info=True)
        return {'error': f"WebSocket communication failed: {str(ws_err)}", 'status': 'websocket_error'}
    except ET.ParseError as xml_err:
        # xml_err does not have a direct way to get the problematic text, but it was logged in _generate_wiki_structure
        logger.error(f"XML parsing error for {repo_full_name}: {xml_err}", exc_info=True)
        return {'error': f"Failed to parse XML structure: {str(xml_err)}", 'status': 'xml_parsing_error'}
    except Exception as e:
        logger.error(f"Unexpected error processing Github repository {repo_full_name}: {str(e)}", exc_info=True)
        return {'error': f"An unexpected error occurred: {str(e)}", 'status': 'unexpected_error'}
