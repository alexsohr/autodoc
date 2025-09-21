import re
import logging
import os
import aiohttp
from typing import Dict, Any

# Import models
from api.web_hook.models.github_events import WikiStructure

# Configure logger
logger = logging.getLogger(__name__)
# Basic config if not already set by another module
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


async def export_wiki_python(
    wiki_structure: WikiStructure,
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
        for page_model_instance in wiki_structure.pages:
            page_id = page_model_instance.id
            content = ""
            if page_id and page_id in generated_pages:
                content = generated_pages[page_id].get('content', "Content not generated")

            page_dict_for_export = page_model_instance.model_dump(exclude_none=True)
            pages_to_export.append({
                **page_dict_for_export,
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
