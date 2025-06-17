import os
import ssl
import aiohttp
import logging

# Configure logger
logger = logging.getLogger(__name__)
# Basic config if not already set by another module
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

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
                logger.info(f"Fetching repository structure from branch: {branch} using url: {api_url}")

                try:
                    async with session.get(api_url, headers=headers) as response:
                        if response.status == 200:
                            tree_data = await response.json()
                            logger.info(f'Successfully fetched repository structure for {owner}/{repo} from branch {branch}')
                            break
                        else:
                            error_data = await response.text()
                            api_error_details = f"Status: {response.status}, Response: {error_data}"
                            logger.error(f"Error fetching repository structure for {owner}/{repo} from branch {branch}: {api_error_details}")
                except Exception as err:
                    logger.error(f"Network error fetching branch {branch} for {owner}/{repo}: {err}")
                    continue # Try next branch if any

        if not tree_data or 'tree' not in tree_data:
            if api_error_details:
                logger.error(f"Could not fetch repository structure for {owner}/{repo}. API Error: {api_error_details}")
            else:
                logger.error(f'Could not fetch repository structure for {owner}/{repo}. Repository might not exist, be empty or private, or no valid branch found.')
            return ""

        # Convert tree data to a string representation (filter for files only)
        file_tree = tree_data['tree']
        file_paths = [
            item['path'] for item in file_tree
            if item.get('type') == 'blob'  # 'blob' represents files, 'tree' represents directories
        ]

        file_tree_string = '\n'.join(file_paths)
        logger.info(f"Successfully generated file tree with {len(file_paths)} files for {owner}/{repo}")
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
            'Accept': 'application/vnd.github.v3.raw' # Request raw content to avoid base64 decoding
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Create SSL context that handles certificate verification issues
        # This might be necessary in environments with self-signed certificates or specific SSL configurations
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False # Consider security implications
        ssl_context.verify_mode = ssl.CERT_NONE    # Consider security implications

        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            logger.info(f"Attempting to fetch README from {api_url} for repo {owner}/{repo}")
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    readme_content = await response.text() # Get raw text
                    logger.info(f"Successfully fetched README for {owner}/{repo}. Length: {len(readme_content)} chars.")
                    return readme_content
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to fetch README for {owner}/{repo} via API (status: {response.status}): {error_text}. It might not exist or be accessible.")
                    return "" # Return empty string if README not found or error occurs

    except Exception as e:
        logger.error(f"Error getting README for {owner}/{repo}: {str(e)}", exc_info=True)
        return ""
