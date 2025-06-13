from typing import List, Dict
import asyncio
import websockets
import json
import logging
from api.web_hook.github_prompts import generate_wiki_page_prompt

MAX_RETRIES = 3

def parse_wiki_pages_from_xml(pages_els) -> List[Dict]:
    """
    Parse <page> elements from XML and return a list of page dicts.
    """
    pages = []
    for page_el in pages_els:
        id_ = page_el.get('id', f'page-{len(pages) + 1}')
        title_el = page_el.find('title')
        importance_el = page_el.find('importance')
        file_path_els = page_el.findall('.//file_path')
        related_els = page_el.findall('.//related')
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
    return pages

def parse_wiki_sections_from_xml(sections_els):
    """
    Parse <section> elements from XML and return (sections, root_sections) lists.
    """
    sections = []
    root_sections = []
    if sections_els:
        for section_el in sections_els:
            id_ = section_el.get('id', f'section-{len(sections) + 1}')
            title_el = section_el.find('title')
            page_ref_els = section_el.findall('.//page_ref')
            section_ref_els = section_el.findall('.//section_ref')
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
                other_section_refs = other_section.findall('.//section_ref')
                for ref in other_section_refs:
                    if ref.text == id_:
                        is_referenced = True
            if not is_referenced:
                root_sections.append(id_)
    return sections, root_sections

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

    logger = logging.getLogger(__name__)
    try:
        # --- Input Validation ---
        if not owner or not repo:
            raise ValueError('Invalid repository information. Owner and repo name are required.')

        # Update generated_pages with a placeholder
        generated_pages[page_id] = {**page, 'content': 'Loading...'}

        # --- Prompt Construction ---
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
                server_base_url = 'http://localhost:8001' # Example
                ws_base_url = server_base_url.replace('http', 'ws')
                ws_url = f"{ws_base_url}/ws/chat"

                try:
                    async with websockets.connect(ws_url) as websocket:
                        logger.info(f"WebSocket connection established for page: {page_title} (attempt {attempt})")
                        await websocket.send(json.dumps(request_body))

                        # Receive messages
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
                    if content:
                        logger.info(f"Successfully generated content for {page_title} via WebSocket on attempt {attempt}, length: {len(content)} characters")
                        break

                except Exception as ws_error:
                    logger.error(f"WebSocket error on attempt {attempt}, falling back to HTTP: {ws_error}")

            except Exception as err:
                last_error = err
                logger.error(f"Attempt {attempt}/{MAX_RETRIES} failed for page {page_id}: {err}")

                if attempt < MAX_RETRIES:
                    wait_time = attempt * 1 # Progressive backoff: 1s, 2s, 3s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

        if not content and last_error:
            raise last_error

        content = content.strip()
        if content.lower().startswith('```markdown'):
            content = content[len('```markdown'):].lstrip()
        if content.lower().endswith('```'):
            content = content[:-len('```')].rstrip()

        updated_page = {**page, 'content': content}
        generated_pages[page_id] = updated_page
        return generated_pages

    except Exception as err:
        logger.error(f"Error generating content for page {page_id} after {MAX_RETRIES} attempts: {err}")
        error_message = str(err) if isinstance(err, Exception) else 'Unknown error'
        generated_pages[page_id] = {**page, 'content': f"Error generating content after {MAX_RETRIES} retries: {error_message}"}
        # This might involve signaling completion for this specific page task. 