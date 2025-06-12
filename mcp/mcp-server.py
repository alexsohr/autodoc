import os
import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastmcp import FastMCP
import httpx
from httpx import HTTPStatusError, ConnectError, TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
AUTODOC_SERVER_URL = os.getenv("AUTODOC_SERVER_URL", "http://localhost:3000")
REQUEST_TIMEOUT = float(os.getenv("MCP_REQUEST_TIMEOUT", "30.0"))
MAX_RETRIES = int(os.getenv("MCP_MAX_RETRIES", "3"))

# Repository URL - can be set via environment variable or passed as argument
REPO_URL = os.getenv("REPO_URL", "")

mcp = FastMCP("AutoDoc MCP Server")

# Create a shared HTTP client with proper configuration
http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client with proper configuration."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True
        )
    return http_client

async def handle_http_error(error: Exception, operation: str) -> Dict[str, Any]:
    """Handle HTTP errors and return structured error response."""
    if isinstance(error, HTTPStatusError):
        logger.error(f"HTTP {error.response.status_code} error during {operation}: {error.response.text}")
        return {
            "error": f"HTTP {error.response.status_code}",
            "message": f"Failed to {operation}",
            "details": error.response.text
        }
    elif isinstance(error, (ConnectError, TimeoutException)):
        logger.error(f"Connection/timeout error during {operation}: {str(error)}")
        return {
            "error": "connection_error",
            "message": f"Unable to connect to AutoDoc server during {operation}",
            "details": str(error)
        }
    else:
        logger.error(f"Unexpected error during {operation}: {str(error)}")
        return {
            "error": "unexpected_error", 
            "message": f"An unexpected error occurred during {operation}",
            "details": str(error)
        }

def validate_repo_url(repo_url: Optional[str] = None) -> bool:
    """Validate that repo_url is properly configured."""
    if not repo_url:
        repo_url = REPO_URL
    if not repo_url or not repo_url.strip():
        logger.error("Repository URL is not configured")
        return False
    return True

def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not value:
        return ""
    # Remove potential harmful characters and limit length
    sanitized = value.strip()[:max_length]
    # Add additional sanitization as needed
    return sanitized

@mcp.tool
async def read_wiki_structure(repo_url: str = REPO_URL) -> Dict[str, Any]:
    """
    Retrieve the complete wiki structure and documentation overview for the configured repository.
    
    This tool provides a comprehensive index of all available documentation pages created by AutoDoc's 
    AI analysis of the repository. Use this first to understand what documentation topics are available 
    before diving into specific content.
    
    The structure includes:
    - Page titles and IDs for navigation
    - Importance levels (high/medium/low) indicating content priority
    - Related pages and cross-references
    - File paths that contributed to each documentation page
    - Overview of the repository's documentation organization
    
    Best used for:
    - Getting an overview of available documentation
    - Understanding the repository's structure and components
    - Finding specific topics before using read_wiki_contents
    - Planning research or documentation exploration
    
    Note: The repository URL is pre-configured via the REPO_URL environment variable in the MCP client 
    configuration, so you don't need to specify it when using this tool.
    
    Returns:
        Dict containing:
        - 'pages': List of documentation pages with titles, IDs, and metadata
        - 'structure': Hierarchical organization of the documentation
        - 'repository_info': Basic repository information and analysis summary
        
        On error: Dict with 'error' and 'message' fields describing the issue.
    
    Example usage:
        "Show me the documentation structure"
        "What topics are covered in the documentation?"
        "List all available wiki pages and their importance levels"
    """
    if not validate_repo_url(repo_url):
        return {"error": "invalid_config", "message": "Repository URL not properly configured"}
    
    params = {"repo_url": repo_url}
    logger.info(f"Fetching wiki structure for repository: {repo_url}")
    
    try:
        client = await get_http_client()
        resp = await client.get(f"{AUTODOC_SERVER_URL}/api/wiki-structure", params=params)
        resp.raise_for_status()
        result = resp.json()
        logger.info("Successfully retrieved wiki structure")
        return result
    except Exception as e:
        return await handle_http_error(e, "fetch wiki structure")

@mcp.tool
async def read_wiki_contents(topic: str, repo_url: str = REPO_URL) -> Dict[str, Any]:
    """
    Retrieve detailed documentation content for a specific topic or page from the configured repository.
    
    This tool fetches the complete content of a documentation page, including markdown text, 
    code examples, diagrams, and metadata. The content is AI-generated based on analysis 
    of the repository's code, structure, and documentation.
    
    Topic identification methods:
    - Page titles: Use exact titles like "Getting Started", "API Documentation", "Features Overview"
    - Page IDs: Use identifiers like "page-1", "page-2", etc.
    - Case-insensitive matching: Both "getting started" and "Getting Started" work
    
    Content includes:
    - Comprehensive markdown documentation
    - Code examples and snippets from the repository
    - Mermaid diagrams showing architecture and data flow
    - File paths that were analyzed to create the content
    - Related topics and cross-references
    - Importance level and metadata
    
    Best used for:
    - Deep diving into specific aspects of the repository
    - Understanding implementation details and architecture
    - Learning how to use or contribute to the project
    - Getting code examples and best practices
    
    Args:
        topic: The documentation topic to retrieve. Can be either:
               - Page title (e.g., "Getting Started", "API Reference")
               - Page ID (e.g., "page-1", "page-2")
               Use read_wiki_structure() first to see available topics.
    
    Note: The repository URL is pre-configured via the REPO_URL environment variable in the MCP client 
    configuration, so you don't need to specify it when using this tool.
    
    Returns:
        Dict containing:
        - 'content': Full markdown content of the documentation page
        - 'title': Page title and description
        - 'filePaths': Source files that contributed to this documentation
        - 'importance': Priority level (high/medium/low)
        - 'relatedPages': IDs of related documentation pages
        - 'id': Unique page identifier
        
        On error: Dict with 'error' and 'message' fields, including suggestions for valid topics.
    
    Example usage:
        "Show me the Getting Started documentation"
        "What does the API Reference page contain?"
        "Read the content of page-3"
        "Get details about the Features Overview"
    """
    if not validate_repo_url(repo_url):
        return {"error": "invalid_config", "message": "Repository URL not properly configured"}
    
    topic = sanitize_input(topic)
    if not topic:
        return {"error": "invalid_input", "message": "Topic parameter is required and cannot be empty"}
    
    params = {"repo_url": repo_url, "topic": topic}
    logger.info(f"Fetching wiki content for topic: {topic}")
    
    try:
        client = await get_http_client()
        resp = await client.get(f"{AUTODOC_SERVER_URL}/api/wiki-content", params=params)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Successfully retrieved content for topic: {topic}")
        return result
    except Exception as e:
        return await handle_http_error(e, f"fetch content for topic '{topic}'")

@mcp.tool
async def ask_question(question: str, repo_url: str = REPO_URL) -> Dict[str, Any]:
    """
    Ask intelligent questions about the configured repository using AI-powered analysis.
    
    This tool leverages AutoDoc's Retrieval Augmented Generation (RAG) system to provide 
    accurate, contextual answers about the repository's code, architecture, and functionality. 
    The AI assistant has deep knowledge of the codebase and can answer both high-level 
    architectural questions and specific implementation details.
    
    Capabilities:
    - Code analysis and explanation
    - Architecture and design pattern identification  
    - Implementation details and best practices
    - Usage instructions and examples
    - Troubleshooting and debugging guidance
    - Development workflow and contribution guidelines
    - API documentation and endpoint explanations
    - Dependencies and technology stack information
    
    Knowledge base constraints:
    - Answers are strictly based on the analyzed repository content
    - Cannot answer questions about external topics or general programming
    - Responses are limited to information found in the codebase and documentation
    - If information isn't available, the assistant will clearly state this
    
    Question types that work well:
    - "How does authentication work in this project?"
    - "What is the main entry point and how does the application start?"
    - "What API endpoints are available and what do they do?"
    - "How is the database schema structured?"
    - "What are the main components and how do they interact?"
    - "How do I set up the development environment?"
    - "What testing frameworks and strategies are used?"
    - "How is error handling implemented?"
    
    Args:
        question: A clear, specific question about the repository. 
                 Best results come from detailed questions about code architecture,
                 implementation patterns, usage instructions, or specific features.
                 Avoid overly broad questions or topics unrelated to the repository.
    
    Note: The repository URL is pre-configured via the REPO_URL environment variable in the MCP client 
    configuration, so you don't need to specify it when using this tool.
    
    Returns:
        Dict containing:
        - 'role': Always "assistant" to indicate AI response
        - 'content': Detailed answer in markdown format with:
          * Code examples and snippets
          * Architecture explanations
          * Usage instructions
          * File references and paths
          * Related concepts and cross-references
        
        On error: Dict with 'error' and 'message' fields describing the issue.
    
    Example usage:
        "How does the authentication system work?"
        "What is the overall architecture of this project?"
        "How do I deploy this application?"
        "What are the main API endpoints and their purposes?"
        "How is data stored and retrieved in this application?"
    """
    if not validate_repo_url(repo_url):
        return {"error": "invalid_config", "message": "Repository URL not properly configured"}
    
    question = sanitize_input(question, max_length=2000)
    if not question:
        return {"error": "invalid_input", "message": "Question parameter is required and cannot be empty"}
    
    payload = {
        "repo_url": repo_url,
        "messages": [{"role": "user", "content": question}],
        "provider": "openai",
        "model": "gpt-4o"
    }
    logger.info(f"Asking question about repository: {question[:100]}{'...' if len(question) > 100 else ''}")
    
    try:
        client = await get_http_client()
        resp = await client.post(f"{AUTODOC_SERVER_URL}/api/chat/complete", json=payload)
        resp.raise_for_status()
        result = resp.json()
        logger.info("Successfully received answer from AI assistant")
        return result
    except Exception as e:
        return await handle_http_error(e, "ask question to AI assistant")



async def cleanup():
    """Clean up resources when the server shuts down."""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None
        logger.info("HTTP client cleaned up")

if __name__ == "__main__":
    try:
        logger.info(f"Starting AutoDoc MCP Server with URL: {AUTODOC_SERVER_URL}")
        logger.info(f"Request timeout: {REQUEST_TIMEOUT}s")
        logger.info(f"Repository URL: {REPO_URL if REPO_URL else 'Not configured - will use tool parameters'}")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown initiated")
    finally:
        asyncio.run(cleanup())
