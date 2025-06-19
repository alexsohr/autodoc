import re
import logging
import xml.etree.ElementTree as ET
import os
import aiohttp
import json
from typing import List, Tuple, Dict, Any

# Import models
from api.web_hook.github_models import WikiStructure, WikiPageDetail, WikiSection # Added WikiPageDetail and WikiSection for test block

# Configure logger
logger = logging.getLogger(__name__)
# Basic config if not already set by another module
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

# Removed temporary placeholder for WikiStructure as it's now imported.

def extract_wiki_structure_xml(wiki_structure_response: str, logger_instance=None) -> str:
    """
    Clean up the AI response and extract the <wiki_structure>...</wiki_structure> XML block.
    Raises ValueError if the response is empty or no valid XML is found.
    """
    if logger_instance is None:
        logger_instance = logger # Use module-level logger if none provided

    if not wiki_structure_response or str(wiki_structure_response).strip() == "":
        logger_instance.error("Wiki structure response is empty - this indicates an issue with the model call")
        raise ValueError("Wiki structure response is empty")

    wiki_structure_response = str(wiki_structure_response)
    # Remove markdown ```xml ... ``` blocks
    wiki_structure_response = re.sub(r'^```(?:xml)?\s*', '', wiki_structure_response, flags=re.IGNORECASE)
    wiki_structure_response = re.sub(r'```\s*$', '', wiki_structure_response, flags=re.IGNORECASE)

    match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", wiki_structure_response, re.MULTILINE)

    if not match:
        logger_instance.error(f"No valid XML structure found in AI response. Response length: {len(wiki_structure_response)}")
        logger_instance.debug(f"Full response for XML extraction check: {wiki_structure_response}")
        if len(wiki_structure_response) > 500:
             logger_instance.debug(f"First 500 chars of response: {wiki_structure_response[:500]}")
        raise ValueError("No valid XML structure found in AI response")

    xml_match = match.group(0)
    # Remove control characters that are invalid in XML
    xml_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_match)
    return xml_text


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

async def export_wiki_python(
    wiki_structure: WikiStructure, # Changed Any to WikiStructure
    generated_pages: dict,
    repo: str,
    repo_url: str,
    export_format: str = 'json',  # 'markdown' or 'json'
    api_base_url: str = ""
) -> tuple[str | None, str | None]:
    """
    Exports the wiki content by calling an API and saving the result.
    """
    logger.info(f"Exporting wiki for {repo} in {export_format} format")

    if not api_base_url:
        api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8001")

    export_error_message: str | None = None

    if not wiki_structure or not hasattr(wiki_structure, 'pages') or not wiki_structure.pages or not generated_pages:
        export_error_message = 'No wiki content to export (wiki_structure, pages, or generated_pages is empty)'
        logger.error(export_error_message)
        return export_error_message, None

    try:
        pages_to_export = []
        for page_data in wiki_structure.pages: # Assuming wiki_structure.pages is a list of dicts
            page_id = page_data.get('id')
            content = ""
            if page_id and page_id in generated_pages:
                content = generated_pages[page_id].get('content', "Content not generated")

            # page_data should already be a dict, spread its contents
            pages_to_export.append({
                **page_data,
                'content': content
            })

        if not pages_to_export:
            export_error_message = "Pages list is empty after processing for export."
            logger.error(export_error_message)
            return export_error_message, None

        payload = {
            'repo_url': repo_url,
            'type': 'github', # This might need to be more dynamic if other types are supported
            'pages': pages_to_export,
            'format': export_format
        }

        api_endpoint = f"{api_base_url.rstrip('/')}/export/wiki"
        logger.info(f"Posting to export API endpoint: {api_endpoint}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if not response.ok: # response.ok is True if status_code < 400
                    error_text = "No error details available from API"
                    try:
                        error_text = await response.text()
                    except Exception as read_err:
                        logger.error(f"Could not read error response text: {read_err}")
                    raise Exception(f"Error exporting wiki (API call failed): {response.status} - {error_text}")

                content_disposition = response.headers.get('Content-Disposition')
                file_ext = 'md' if export_format == 'markdown' else 'json'
                repo_name_for_file = repo.replace("/", "_") # Sanitize repo name for filename
                filename = f"{repo_name_for_file}_wiki.{file_ext}"

                if content_disposition:
                    match = re.search(r'filename=(?:"([^"]+)"|([^;]+))', content_disposition)
                    if match:
                        extracted_filename = match.group(1) or match.group(2)
                        if extracted_filename:
                            filename = extracted_filename.strip()

                blob_data = await response.read()

                # Ensure 'downloads' directory exists
                downloads_dir = "downloads"
                os.makedirs(downloads_dir, exist_ok=True)
                save_path = os.path.join(downloads_dir, filename)

                with open(save_path, 'wb') as f:
                    f.write(blob_data)

                logger.info(f"Wiki exported successfully to: {os.path.abspath(save_path)}")
                return None, os.path.abspath(save_path)

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error during wiki export for repo {repo}: {error_message}", exc_info=True)
        return error_message, None
    finally:
        logger.info(f"Export process finished for repo {repo}.")


def clean_and_format_content(content: str) -> str:
    """
    Cleans up HTML tags and source links from the content,
    and removes specific patterns like mermaid diagrams and details tags.
    """
    if not isinstance(content, str):
        logger.warning("Content to clean is not a string. Returning as is.")
        return content

    # Remove <details> and <summary> tags and their content
    content = re.sub(r'<details>.*?</details>', '', content, flags=re.DOTALL)

    # Remove `Sources: [...]()` or `Source: [...]()`
    content = re.sub(r'`Sources?: \[.*?\]\(\)`', '', content, flags=re.IGNORECASE) # Made Sources? optional

    # Remove markdown image links ![text](url)
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

    # Remove markdown links [text](url) but keep the text
    content = re.sub(r'\[(.*?)\]\(https?://[^\s)]+\)', r'\1', content)

    # Remove any remaining HTML tags
    content = re.sub(r'<[^>]*>', '', content)

    # Remove mermaid diagrams
    content = re.sub(r'```mermaid.*?```', '', content, flags=re.DOTALL)

    # Clean up multiple blank lines to a maximum of two
    content = re.sub(r'\n\s*\n', '\n\n', content).strip()
    return content

def generate_llms_txt(data: Dict[str, Dict[str, Any]], filename: str ="llms.txt") -> None:
    """
    Converts the dictionary data into a good-looking text file.
    Each page is formatted with its title, content, importance, related pages, and file paths.
    """
    try:
        output_dir = "repo_wiki_generations"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for page_id, page_data in data.items():
                title = page_data.get('title', page_id.replace('-', ' ').title())
                content = page_data.get('content', '')
                importance = page_data.get('importance', 'N/A')
                # Ensure relatedPages and filePaths are lists before join
                related_pages_list = page_data.get('relatedPages', [])
                related_pages = ", ".join(related_pages_list) if isinstance(related_pages_list, list) and related_pages_list else 'None'

                file_paths_list = page_data.get('filePaths', [])
                file_paths = ", ".join(file_paths_list) if isinstance(file_paths_list, list) and file_paths_list else 'None'

                cleaned_content = clean_and_format_content(str(content)) # Ensure content is string

                f.write(f"# {title}\n")
                f.write("-" * (len(title) + 2) + "\n\n") # Underline for emphasis

                f.write(f"**ID:** {page_data.get('id', page_id)}\n") # Use page_id if 'id' field is missing
                f.write(f"**Importance:** {str(importance).capitalize()}\n") # Ensure importance is string
                f.write(f"**Related Pages:** {related_pages}\n")
                f.write(f"**Relevant Files:** {file_paths}\n\n")

                f.write("## Content\n")
                f.write(cleaned_content + "\n\n")
                f.write("---" * 10 + "\n\n") # Separator between pages
        logger.info(f"Successfully generated llms.txt at {filepath}")
    except Exception as e:
        logger.error(f"Error generating llms.txt: {e}", exc_info=True)

# from api.web_hook.github_models import WikiStructure # Already imported at the top

# Example usage (for testing, can be removed or kept for utility testing)
if __name__ == '__main__':
    # Example for generate_llms_txt
    sample_data = {
        "page-1": {
            "id": "page-1",
            "title": "Introduction to Project",
            "content": "This is the main introduction. ```mermaid\ngraph TD;\nA-->B;\n``` Some more text. <p>HTML paragraph</p> [A link](http://example.com)",
            "importance": "high",
            "relatedPages": ["page-2"],
            "filePaths": ["src/main.py", "README.md"]
        },
        "page-2": {
            "id": "page-2",
            "title": "Advanced Topics",
            "content": "Details about advanced stuff. Source: [docs](http://example.com/docs)",
            "importance": "medium",
            "relatedPages": [],
            "filePaths": ["src/advanced.py"]
        }
    }
    generate_llms_txt(sample_data, "test_llms.txt")
    logger.info("Test llms.txt generated.")

    # Example for extract_wiki_structure_xml
    sample_xml_response = """
    ```xml
    <wiki_structure>
        <title>Test Wiki</title>
        <description>This is a test wiki.</description>
        <pages>
            <page id="p1">
                <title>Page 1</title>
                <description>Content for page 1.</description>
                <importance>high</importance>
                <file_path>file1.txt</file_path>
            </page>
        </pages>
    </wiki_structure>
    ```
    """
    try:
        extracted = extract_wiki_structure_xml(sample_xml_response)
        logger.info(f"Extracted XML: {extracted}")
        title, desc, pages = parse_wiki_structure(extracted)
        logger.info(f"Parsed: Title='{title}', Desc='{desc}', Pages={pages}")
    except ValueError as ve:
        logger.error(f"Error in XML processing test: {ve}")

    # Example for clean_and_format_content
    dirty_text = "<details><summary>Click me</summary>Hidden details.</details>This is `Sources: [source](http://example.com)` visible. ![img](img.png) [link](http://example.com/link)"
    cleaned = clean_and_format_content(dirty_text)
    logger.info(f"Cleaned text: '{cleaned}'")

    # Async function test (basic)
    async def test_export():
        # Create a dummy WikiStructure-like object using the imported model
        # Pages should be list of WikiPageDetail instances or dicts that match its fields
        dummy_pages_list_of_dicts = [
            {
                'id': 'p1',
                'title': 'Test Page 1',
                'description': 'Desc for P1',
                'importance': 'high',
                'file_paths': ['file1.py'],
                'related_pages': ['p2'],
                'content': 'Initial content for p1'
            }
        ]
        # Convert dicts to WikiPageDetail instances
        dummy_page_models = [WikiPageDetail(**pd) for pd in dummy_pages_list_of_dicts]

        # Sections should be list of WikiSection instances or dicts
        dummy_sections_list_of_dicts = [
            {
                'id': 's1',
                'title': 'Section 1',
                'pages': ['p1'],
                'subsections': []
            }
        ]
        dummy_section_models = [WikiSection(**sd) for sd in dummy_sections_list_of_dicts]

        try:
            dummy_wiki_structure_obj = WikiStructure(
                id="dummy_wiki_id",
                title="Dummy Wiki Test",
                description="A test wiki structure for export_wiki_python.",
                pages=dummy_page_models, # Now using list of WikiPageDetail models
                sections=dummy_section_models, # Now using list of WikiSection models
                root_sections=['s1']
            )
            generated_content_map = {"p1": {"content": "This is the fully generated content for p1."}}
            logger.info("Testing export_wiki_python (requires a mock or live API endpoint for full test)")

            # The export_wiki_python function is async, so it needs to be awaited.
            # This test might still fail if the API endpoint it calls is not available.
            # err, path = await export_wiki_python(dummy_wiki_structure_obj, generated, "test_repo", "http://example.com/repo")
            # if err:
            #     logger.error(f"Test export failed: {err}")
            # else:
            #     logger.info(f"Test export successful, file at: {path}")
        except Exception as e:
            logger.error(f"Error creating dummy WikiStructure or running test_export: {e}")

    import asyncio
    # To run the async test_export function:
    # asyncio.run(test_export()) # This line can be uncommented to run the test.
    # Note: Running asyncio.run() might cause issues if an event loop is already running (e.g. in Jupyter or some frameworks).
    # Consider this if __name__ == '__main__' is executed in such environments.

    logger.info("Utils.py script finished its __main__ block execution.")
