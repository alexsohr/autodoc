import os
import asyncio
from typing import Any
from urllib.parse import quote

from fastmcp import FastMCP, ServerSideParameter, tool
import httpx

# Read the main AutoDoc server URL from environment variable
AUTODOC_SERVER_URL = os.getenv("AUTODOC_SERVER_URL", "http://localhost:3000")

mcp = FastMCP("AutoDoc MCP Server")

# Define repo_url as a server-side parameter (required at connection time)
repo_url = ServerSideParameter[str]("repo_url", description="Target repository URL")

@tool
async def read_wiki_structure() -> Any:
    """Return the wiki structure for the configured repository."""
    params = {"repo_url": repo_url.value}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{AUTODOC_SERVER_URL}/api/wiki-structure", params=params)
        resp.raise_for_status()
        return await resp.json()

@tool
async def read_wiki_contents(topic: str) -> Any:
    """Return the wiki content for a specific topic."""
    params = {"repo_url": repo_url.value, "topic": topic}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{AUTODOC_SERVER_URL}/api/wiki-content", params=params)
        resp.raise_for_status()
        return await resp.json()

@tool
async def ask_question(question: str) -> Any:
    """Ask a question about the repository using the AutoDoc chat endpoint."""
    payload = {
        "repo_url": repo_url.value,
        "messages": [{"role": "user", "content": question}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{AUTODOC_SERVER_URL}/api/chat/complete", json=payload)
        resp.raise_for_status()
        return await resp.json()

if __name__ == "__main__":
    mcp.run()
