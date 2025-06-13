import unittest
from api.web_hook.github_models import WikiStructure
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.web_hook.github_api import process_github_repository_async, export_wiki_python
from api.web_hook.github_api import app


class TestGitHubAPI(unittest.TestCase):
    """
    Test suite for Github API functionality.
    """
    def setUp(self):
        """
        Set up test environment before each test.
        """
        self.test_client = TestClient(app)
        self.raw_json = {
            "number": 1,
            "action": "closed",
            "repository": {
                "id": 1001069502,
                "full_name": "Taha-1005/webhook_autodoc",
                "private": False,
                "owner": {
                    "login": "Taha-1005",
                    "id": 82571791
                },
                "html_url": "https://github.com/Taha-1005/webhook_autodoc",
                "default_branch": "main"
            },
            "pull_request": {
                "merged": True,
                "base": {
                    "ref": "main"
                }
            }
        }
        self.headers_mock = {
            "X-Hub-Signature": "sha256=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request"
        }
        # Environmental setup for testing
        os.environ["SERVER_BASE_URL"] = "http://localhost:8001"

    @patch('api.web_hook.github_api.hmac.compare_digest')
    def test_github_webhook(self, mock_compare_digest):
        """
        Test Github webhook endpoint with a sample payload.
        """
        mock_compare_digest.return_value = True
        response = self.test_client.post(
            "/webhook",
            json=self.raw_json,
            headers=self.headers_mock
        )
        self.assertEqual(response.status_code, 202)

    
    @patch('websockets.connect')
    @patch('api.web_hook.github_api.hmac.compare_digest')
    def test_github_webhook_mocked_export(self, mock_compare_digest, mock_ws_connect):
        """
        Test Github webhook endpoint with a sample payload.
        """
        mock_compare_digest.return_value = True
        mock_ws = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws
        mock_ws.__aiter__.return_value = {
    'introduction': {
        'id': 'introduction',
        'title': 'Introduction',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [README.md](README.md)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [instructions/features.md](instructions/features.md)\n- [api/openrouter_client.py](api/openrouter_client.py)\n</details>\n\n# Introduction\n\nAutoDoc is a tool designed to automatically generate documentation for software repositories by leveraging AI analysis. It aims to simplify the process of creating and maintaining comprehensive documentation, making it easier for developers to understand, use, and contribute to projects. The tool uses a combination of code analysis and large language models (LLMs) to produce detailed documentation, including API references, architecture overviews, and usage examples.\n\nThe AutoDoc MCP Server acts as a bridge between the auto-generated documentation and AI assistants, enabling users to browse the documentation structure, read detailed content, and ask intelligent questions about the repository using RAG-powered AI. This introduction will provide an overview of AutoDoc\'s features, architecture, and usage, highlighting its benefits for both developers and users.\n\n## Overview of AutoDoc\n\nAutoDoc automates the generation of documentation for software repositories. It analyzes the code, structure, and documentation within a repository to create a comprehensive wiki. This includes page titles and IDs for navigation, importance levels indicating content priority, related pages and cross-references, and file paths that contributed to each documentation page. The generated documentation is designed to help users understand the repository\'s structure, components, and functionality.  The system also supports integration with Model Context Protocol (MCP) for enhanced interaction with AI assistants. [README.md]()\n\n## Key Features\n\nAutoDoc offers several key features that streamline the documentation process:\n\n*   **Automated Documentation Generation:** Automatically generates documentation by analyzing the repository\'s code and structure.\n*   **AI-Powered Content Creation:** Uses AI to create detailed documentation, including API references, architecture overviews, and usage examples.\n*   **Comprehensive Wiki Structure:** Organizes documentation into a structured wiki with page titles, IDs, and cross-references.\n*   **Integration with AI Assistants:** Supports integration with AI assistants through the Model Context Protocol (MCP). [README.md]()\n*   **llms.txt Generation:** Creates an `llms.txt` file to improve LLM interactions with the repository. [instructions/features.md]()\n\n## AutoDoc MCP Server\n\nThe AutoDoc MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) implementation that allows AI assistants to directly access the documentation and analysis capabilities generated by AutoDoc. It provides a bridge between the auto-generated documentation and AI assistants, enabling users to:\n\n*   Browse Documentation Structure\n*   Read Detailed Content\n*   Ask Intelligent Questions using RAG-powered AI [README.md]()\n\n### Available Tools\n\nThe MCP server provides two main tools:\n\n1.  `read_wiki_structure`: Retrieves the complete wiki structure and documentation overview.\n2.  `read_wiki_contents`: Retrieves detailed documentation content for a specific topic or page. [README.md]()\n\n### Using the Tools\n\nTo use these tools, you can send requests to the MCP server with the appropriate parameters. For example, to retrieve the wiki structure, you can use the `read_wiki_structure` tool. To retrieve the content of a specific page, you can use the `read_wiki_contents` tool with the page title or ID as the topic. [mcp/mcp-server.py]()\n\n## llms.txt File Generation\n\nAutoDoc generates an `llms.txt` file to enhance interactions with Large Language Models (LLMs). This file acts as a curated "table of contents" or a high-level summary, pointing the LLM directly to the most important, AI-friendly information. It saves processing time and improves the accuracy of the LLM\'s understanding. [instructions/features.md]()\n\n### Implementation\n\nThe `llms.txt` file is generated dynamically after the main documentation/wiki is created. The file includes:\n\n*   An H1 title with the repository name.\n*   A blockquote summary generated by an LLM call.\n*   H2 sections and links to major topics or pages in the wiki. [instructions/features.md]()\n\n## Conclusion\n\nAutoDoc simplifies the process of creating and maintaining documentation for software repositories. By automating documentation generation and leveraging AI-powered content creation, AutoDoc makes it easier for developers to understand, use, and contribute to projects. The integration with AI assistants through the MCP server further enhances the accessibility and usability of the generated documentation.',
        'filePaths': ['README.md'],
        'importance': 'high',
        'relatedPages': ['quick-start', 'data-flow']
    },
    'quick-start': {
        'id': 'quick-start',
        'title': 'Quick Start',
        'content': '<details>\n<summary>Relevant source files</summary>\n\n- [mcp/README.md](mcp/README.md)\n- [docker-compose.yml](docker-compose.yml)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n- [api/data_pipeline.py](api/data_pipeline.py)\n</details>\n\n# Quick Start\n\nThe AutoDoc MCP Server facilitates interaction with AI assistants by providing access to repository documentation and analysis capabilities generated by AutoDoc. It leverages the Model Context Protocol (MCP) to bridge AutoDoc-generated documentation and AI assistants. This allows users to browse the repository\'s wiki, read detailed content, and ask intelligent questions using RAG-powered AI. The server uses HTTP APIs to communicate with a running AutoDoc instance, ensuring responses are based on the repository\'s code and documentation.  `Sources: [mcp/README.md]()`\n\nThis quick start guide will walk you through setting up and using the AutoDoc MCP Server.\n\n## Prerequisites\n\n*   Docker installed and running.\n*   An AutoDoc instance running and accessible.\n\n## Installation and Setup\n\n1.  **Clone the repository:**\n\n    ```bash\n    git clone <repository_url>\n    cd webhook_autodoc\n    ```\n    (Note: Replace `<repository_url>` with the actual repository URL.)\n2.  **Configure Environment Variables:**\n\n    The MCP server requires certain environment variables to be configured. These can be set directly in your shell or using a `.env` file.\n\n    *   `REPO_URL`: The URL of the repository you want to document.  `Sources: [mcp/mcp-server.py:63,77,130]()`\n    *   `OPENROUTER_API_KEY`: API key for OpenRouter.  `Sources: [api/openrouter_client.py]()`\n    *   `OR_MODEL`: OpenRouter model to use.  `Sources: [api/openrouter_client.py]()`\n\n3.  **Run with Docker Compose:**\n\n    The easiest way to get started is using Docker Compose.  The `docker-compose.yml` file defines the necessary services and configurations.\n\n    ```bash\n    docker-compose up -d\n    ```\n\n    This command builds and starts the MCP server in detached mode.  `Sources: [docker-compose.yml]()`\n\n    The `docker-compose.yml` file sets up the mcp-server service.  `Sources: [docker-compose.yml]()` It defines the image, ports, volumes, and environment variables required to run the server.  `Sources: [docker-compose.yml]()`\n\n    ```yaml\n    version: "3.8"\n    services:\n      mcp-server:\n        image: tiangolo/uvicorn-gunicorn-fastapi:python3.11\n        command: uvicorn mcp.mcp-server:app --host 0.0.0.0 --port 8000 --workers 1\n        volumes:\n          - ./mcp:/app/mcp\n          - ./api:/app/api\n        ports:\n          - "8000:8000"\n        environment:\n          - REPO_URL=${REPO_URL}\n          - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}\n          - OR_MODEL=${OR_MODEL}\n    ```\n    `Sources: [docker-compose.yml]()`\n\n4.  **Verify the Setup:**\n\n    Once the Docker container is running, you can verify that the MCP server is accessible by sending a request to the `/docs` endpoint.\n\n## Available Tools\n\nThe AutoDoc MCP Server provides the following tools:\n\n### 1. `read_wiki_structure`\n\nThis tool retrieves the complete wiki structure and documentation overview for the configured repository.  `Sources: [mcp/README.md]()` It provides an index of all available documentation pages created by AutoDoc\'s AI analysis.  `Sources: [mcp/README.md]()`\n\n**Returns:**\n\n*   Page titles and IDs for navigation.  `Sources: [mcp/README.md]()`\n*   Importance levels (high/medium/low) indicating content priority.  `Sources: [mcp/README.md]()`\n*   Related pages and cross-references.  `Sources: [mcp/README.md]()`\n*   File paths that contributed to each documentation page.  `Sources: [mcp/README.md]()`\n*   Overview of the repository\'s documentation organization.  `Sources: [mcp/README.md]()`\n\n### 2. `read_wiki_contents`\n\nThis tool retrieves detailed documentation content for a specific topic or page from the configured repository.  `Sources: [mcp/README.md]()` It fetches the complete content of a documentation page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/README.md]()` The content is AI-generated based on analysis of the repository\'s code, structure, and documentation.  `Sources: [mcp/README.md]()`\n\n**Parameters:**\n\n*   `topic` (string): The documentation topic to retrieve. Can be either:\n    *   Page title (e.g., "Getting Started", "API Reference")  `Sources: [mcp/README.md]()`\n    *   Page ID (e.g., "page-1", "page-2")  `Sources: [mcp/README.md]()`\n\n**Topic Identification Methods:**\n\n*   **Page titles**: Use exact titles like "Getting Started", "API Documentation", "Features Overview".  `Sources: [mcp/README.md]()`\n*   **Page IDs**: Use identifiers like "page-1", "page-2", etc.  `Sources: [mcp/README.md]()`\n*   **Case-insensitive matching**: Both "getting started" and "Getting Started" work.  `Sources: [mcp/README.md]()`\n\n## Usage Examples\n\nThe `read_wiki_structure` and `read_wiki_contents` tools can be accessed via HTTP requests to the MCP server.  The `read_wiki_structure` tool retrieves the wiki structure.  `Sources: [mcp/mcp-server.py]()` The `read_wiki_contents` tool retrieves the content of a specific topic.  `Sources: [mcp/mcp-server.py]()`\n\n### Example: Retrieving Wiki Structure\n\n```python\nimport requests\n\nurl = "http://localhost:8000/read_wiki_structure"  # Replace with your server\'s address\nparams = {"repo_url": "[https://github.com/Taha-1005/webhook_autodoc](https://github.com/Taha-1005/webhook_autodoc)"}  # Replace with your repo URL\n\nresponse = requests.get(url, params=params)\n\nif response.status_code == 200:\n    data = response.json()\n    print(data)\nelse:\n    print(f"Error: {response.status_code} - {response.text}")\n```\n\n### Example: Retrieving Wiki Contents\n\n```python\nimport requests\n\nurl = "http://localhost:8000/read_wiki_contents"  # Replace with your server\'s address\nparams = {\n    "repo_url": "[https://github.com/Taha-1005/webhook_autodoc](https://github.com/Taha-1005/webhook_autodoc)",  # Replace with your repo URL\n    "topic": "Quick Start"  # Replace with the desired topic\n}\n\nresponse = requests.get(url, params=params)\n\nif response.status_code == 200:\n    data = response.json()\n    print(data)\nelse:\n    print(f"Error: {response.status_code} - {response.text}")\n```\n\n## Conclusion\n\nThis guide provided a quick start to setting up and using the AutoDoc MCP Server. By following these steps, you can easily integrate your AutoDoc-generated documentation with AI assistants, enabling powerful new ways to interact with your repository\'s knowledge.',
        'filePaths': ['README.md', 'docker-compose.yml'],
        'importance': 'high',
        'relatedPages': ['introduction', 'docker-setup']
    },
    'data-flow': {
        'id': 'data-flow',
        'title': 'Data Flow',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [api/data_pipeline.py](api/data_pipeline.py)\n- [api/rag.py](api/rag.py)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [README.md](README.md)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n</details>\n\n# Data Flow\n\nThis page outlines the data flow within the AutoDoc project, focusing on how data is processed from repository analysis to providing documentation and answering user queries. It covers the key components involved in data ingestion, processing, and retrieval, highlighting the roles of different modules and APIs. The data flow includes repository analysis, wiki structure determination, content generation, and serving documentation via the MCP server.\n\n## Repository Analysis and Wiki Generation\n\nThe data flow begins with the analysis of a repository to determine its structure and generate documentation. This process is initiated by the `determineWikiStructure` function in `src/app/[owner]/[repo]/page.tsx`. This function orchestrates the analysis of the repository\'s file tree and README content to create a wiki structure. The determined structure is then used to generate individual wiki pages. The overall process involves several steps:\n\n1.  **Repository Information Gathering:** The `determineWikiStructure` function first gathers repository information, including the owner and repository name, to construct the repository URL. It then prepares a request body containing the repository URL, repository type, and a prompt for the AI model to analyze the repository and create a wiki structure.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n2.  **Wiki Structure Determination:** The request is sent to the backend, where the AI model analyzes the file tree and README content to determine a logical wiki structure. The AI model suggests pages, sections, and their relationships based on the repository\'s content.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n3.  **Content Generation:** Once the wiki structure is determined, the system generates content for each page, incorporating code snippets, diagrams, and explanations extracted from the repository.  `Sources: [api/data_pipeline.py](), [api/rag.py]()`\n\n```mermaid\ngraph TD\n    A[Repository File Tree & README] --> B(determineWikiStructure);\n    B --> C{AI Model};\n    C --> D[Wiki Structure (pages, sections)];\n    D --> E(Content Generation);\n    E --> F[Wiki Pages (Markdown)];\n```\n\nThis diagram illustrates the initial steps of the data flow, from gathering repository information to generating wiki pages. The `determineWikiStructure` function plays a central role in initiating this process.\n\n## Serving Documentation via MCP Server\n\nThe AutoDoc MCP Server facilitates access to the generated documentation via AI assistants. The server implements the Model Context Protocol (MCP) to provide a seamless bridge between the generated documentation and AI assistants like Claude Desktop and Cursor.  `Sources: [mcp/README.md]()`\n\n### MCP Server Tools\n\nThe MCP server provides several tools for accessing the documentation:\n\n1.  **`read_wiki_structure`:** This tool retrieves the complete wiki structure and documentation overview for the configured repository. It provides an index of all available documentation pages, including titles, IDs, importance levels, and related pages.  `Sources: [mcp/mcp-server.py](), [mcp/README.md]()`\n2.  **`read_wiki_contents`:** This tool retrieves detailed documentation content for a specific topic or page from the configured repository. It fetches the complete content of a documentation page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/mcp-server.py](), [mcp/README.md]()`\n\n### Data Flow within MCP Server\n\nThe data flow within the MCP server involves receiving requests from AI assistants, retrieving the requested documentation content, and returning the content to the AI assistant.\n\n```mermaid\nsequenceDiagram\n    participant AI Assistant\n    participant MCP Server\n    participant Data Store\n\n    AI Assistant->>MCP Server: Request documentation (topic/page ID)\n    activate MCP Server\n    MCP Server->>Data Store: Retrieve documentation content\n    activate Data Store\n    Data Store-->>MCP Server: Documentation content\n    deactivate Data Store\n    MCP Server-->>AI Assistant: Documentation content\n    deactivate MCP Server\n```\n\nThis sequence diagram illustrates the data flow within the MCP server, from receiving requests from AI assistants to retrieving and returning documentation content. The MCP server acts as an intermediary between the AI assistant and the data store.\n\n### Code Snippet: `read_wiki_contents`\n\n```python\n@mcp.tool\nasync def read_wiki_contents(topic: str, repo_url: str = REPO_URL) -> Dict[str, Any]:\n    """\n    Retrieve detailed documentation content for a specific topic or page from the configured repository.\n    """\n    # Implementation details for retrieving documentation content\n    pass\n```\n\nThis code snippet shows the `read_wiki_contents` tool in the MCP server, which retrieves detailed documentation content for a specific topic or page.  `Sources: [mcp/mcp-server.py]()`\n\n## RAG-Powered AI for Answering Questions\n\nThe project utilizes Retrieval-Augmented Generation (RAG) to answer user questions based on the repository\'s documentation. The RAG pipeline involves retrieving relevant documents based on the user\'s query and generating an answer using an AI model.  `Sources: [api/rag.py]()`\n\n### RAG Pipeline Steps\n\n1.  **User Query:** The user submits a question or query related to the repository.\n2.  **Document Retrieval:** The RAG system retrieves relevant documents from the documentation based on the user\'s query. This involves embedding the query and documents and finding the documents with the most similar embeddings.  `Sources: [api/rag.py]()`\n3.  **Answer Generation:** The AI model generates an answer based on the retrieved documents and the user\'s query. This involves feeding the query and retrieved documents to the AI model and generating a coherent and informative answer.  `Sources: [api/rag.py]()`\n\n### Data Flow Diagram for RAG\n\n```mermaid\ngraph TD\n    A[User Query] --> B(Document Retrieval);\n    B --> C{AI Model};\n    C --> D[Generated Answer];\n```\n\nThis diagram illustrates the data flow in the RAG pipeline, from the user query to the generated answer. The document retrieval and AI model components play key roles in this process.\n\n## Conclusion\n\nThe data flow within the AutoDoc project encompasses repository analysis, wiki generation, serving documentation via the MCP server, and answering user queries using RAG. The project leverages AI models and various modules to process data and provide comprehensive documentation and answers. Understanding the data flow is crucial for developers working on or learning about the project, as it provides insights into the system\'s architecture and functionality.',
        'filePaths': ['README.md', 'api/rag.py', 'api/data_pipeline.py'],
        'importance': 'medium',
        'relatedPages': ['project-structure', 'ask-deepresearch']
    },
    'project-structure': {
        'id': 'project-structure',
        'title': 'Project Structure',
        'content': "<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [src/app/[owner]/[repo]/page.tsx](src/app/[owner]/[repo]/page.tsx)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [mcp/README.md](mcp/README.md)\n- [src/app/[owner]/[repo]/slides/page.tsx](src/app/[owner]/[repo]/slides/page.tsx)\n- [instructions/features.md](instructions/features.md)\n</details>\n\n# Project Structure\n\nThis document provides an overview of the project structure, focusing on key components and their relationships. It covers the client-side application structure, the Model Context Protocol (MCP) server, API endpoints, and supporting files that contribute to the project's functionality. This structure enables AI assistants to access repository documentation and analysis capabilities.\n\n## Client-Side Application Structure\n\nThe client-side application is primarily located in the `src/app` directory. The `[owner]/[repo]` directory structure suggests a dynamic routing system based on the repository owner and name. Key files include `page.tsx` and `slides/page.tsx`.\n\n### `page.tsx`\n\nThis file appears to be the main page component for displaying the wiki content. It fetches and displays the wiki structure and generated pages. It uses `getRepoUrl` to construct the repository URL and interacts with the backend to determine the wiki structure using the `determineWikiStructure` function. This function takes the file tree and README content as input to create a logical wiki structure. It also handles loading states and error conditions.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n\n### `slides/page.tsx`\n\nThis file is responsible for generating slide content from the wiki data. It retrieves wiki data and structures it into slides, prioritizing high-importance pages. It limits the total content length to avoid token limits.  `Sources: [src/app/[owner]/[repo]/slides/page.tsx]()`\n\n## Model Context Protocol (MCP) Server\n\nThe MCP server, implemented in `mcp/mcp-server.py`, acts as a bridge between the AutoDoc-generated documentation and AI assistants. It is built using FastMCP and allows AI assistants to browse documentation structure, read detailed content, and ask intelligent questions.  `Sources: [mcp/README.md]()`\n\n### Available Tools\n\nThe MCP server provides two main tools: `read_wiki_structure` and `read_wiki_contents`.  `Sources: [mcp/README.md]()`\n\n1.  **`read_wiki_structure`**: This tool retrieves the complete wiki structure and documentation overview for the configured repository. It provides page titles, IDs, importance levels, related pages, and file paths.  `Sources: [mcp/README.md]()`\n2.  **`read_wiki_contents`**: This tool retrieves detailed documentation content for a specific topic or page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/README.md]()`\n\n### Key Functions\n\n*   **`read_wiki_structure(repo_url: str = REPO_URL)`**: Retrieves the wiki structure.  `Sources: [mcp/mcp-server.py]()`\n*   **`read_wiki_contents(topic: str, repo_url: str = REPO_URL)`**: Retrieves detailed documentation content for a specific topic.  `Sources: [mcp/mcp-server.py]()`\n\n## API Endpoints\n\nThe project includes API endpoints for interacting with external services and handling requests.\n\n### `api/openrouter_client.py`\n\nThis file likely contains the implementation for interacting with the OpenRouter API.  The content of this file was not available in the provided documents.\n\n### `api/websocket_wiki.py`\n\nThis file seems to handle WebSocket communication for wiki-related functionalities. It defines system prompts for different stages of a deep research process. These prompts guide the AI in analyzing the repository and generating documentation.  `Sources: [api/websocket_wiki.py]()`\n\n#### System Prompts\n\nThe system prompts are designed for multi-turn deep research, focusing on specific topics within the repository. The prompts vary based on the research iteration and whether it's the final iteration. They instruct the AI to provide detailed, focused information, synthesize findings, and maintain continuity with previous research.  `Sources: [api/websocket_wiki.py]()`\n\n## Supporting Files\n\nSeveral supporting files contribute to the project's overall structure and functionality.\n\n### `instructions/features.md`\n\nThis file outlines the implementation plan for various features, including the dynamic generation of an `llms.txt` file. This file acts as a curated table of contents, pointing LLMs to the most important, AI-friendly information.  `Sources: [instructions/features.md]()`\n\n### `llms.txt`\n\nThe `llms.txt` file, dynamically generated, contains a summary of the project and links to key modules and documentation pages. It improves the accuracy and efficiency of LLM interactions with the repository.  `Sources: [instructions/features.md]()`\n\n## Architecture Diagram\n\n```mermaid\ngraph TD\n    A[Client-Side Application] --> B(page.tsx);\n    A --> C(slides/page.tsx);\n    B --> D{Determine Wiki Structure};\n    D --> E[File Tree & README];\n    E --> F(Backend API);\n    F --> G(mcp/mcp-server.py);\n    G --> H{read_wiki_structure};\n    G --> I{read_wiki_contents};\n    I --> J[Documentation Content];\n    H --> K[Wiki Structure];\n    style A fill:#f9f,stroke:#333,stroke-width:2px\n    style G fill:#ccf,stroke:#333,stroke-width:2px\n```\n\nThis diagram illustrates the high-level architecture, showing the interaction between the client-side application, backend API, and MCP server.  `Sources: [src/app/[owner]/[repo]/page.tsx](), [mcp/mcp-server.py]()`\n\n## Conclusion\n\nThe project structure is designed to facilitate AI-driven documentation and analysis of code repositories. The client-side application provides a user interface for Browse the generated wiki, while the MCP server enables AI assistants to access detailed documentation content. The API endpoints and supporting files ensure seamless integration and efficient interaction with external services.",
        'filePaths': ['README.md'],
        'importance': 'medium',
        'relatedPages': ['api-server', 'mcp-server']
    },
    'ask-deepresearch': {
        'id': 'ask-deepresearch',
        'title': 'Ask & DeepResearch Features',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [README.md](README.md)\n- [src/components/Ask.tsx](src/components/Ask.tsx)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [mcp/README.md](mcp/README.md)\n</details>\n\n# Ask & DeepResearch Features\n\nThe Ask and DeepResearch features in this project provide users with the ability to interact with the repository\'s documentation and code through natural language queries. The Ask feature delivers context-aware responses using Retrieval Augmented Generation (RAG), while DeepResearch conducts multi-turn investigations to provide comprehensive answers to complex questions. These features enhance the accessibility and understanding of the codebase, making it easier for users to learn, contribute, and troubleshoot.\n\n## Ask Feature\n\nThe Ask feature allows users to pose questions about the repository and receive answers grounded in the actual code. It leverages Retrieval Augmented Generation (RAG) to provide context-aware responses. The system retrieves relevant code snippets to provide grounded responses. Responses are generated in real-time, providing an interactive experience. Source: [README.md]()\n\n### RAG-Powered Responses\n\nThe Ask feature uses Retrieval Augmented Generation (RAG) to generate responses based on the repository\'s content. The AI assistant uses a knowledge base constrained by the analyzed repository content and cannot answer questions about external topics or general programming. If information isn\'t available, the assistant will clearly state this. Source: [mcp/mcp-server.py]()\n\n### Usage\n\nThe `ask_question` tool in `mcp-server.py` provides the RAG functionality. It takes a question as input and returns a detailed answer in markdown format, including code examples, architecture explanations, and usage instructions. Source: [mcp/mcp-server.py]()\n\nExample questions that work well include:\n\n- "How does authentication work in this project?"\n- "What is the main entry point and how does the application start?"\n- "What API endpoints are available and what do they do?"\n- "How is the database schema structured?"\n- "What are the main components and how do they interact?"\n- "How do I set up the development environment?"\n- "What testing frameworks and strategies are used?"\n- "How is error handling implemented?" Source: [mcp/mcp-server.py]()\n\n### Ask Component\n\nThe `Ask` component in `src/components/Ask.tsx` provides the user interface for the Ask feature. It includes a form for submitting questions and displays the AI-generated response. Source: [src/components/Ask.tsx]()\n\n## DeepResearch Feature\n\nThe DeepResearch feature conducts multi-turn investigations to provide comprehensive answers to complex questions. It is enabled by checking the "Deep Research" option in the UI. When enabled, the AI automatically continues research until complete (up to 5 iterations). Source: [src/components/Ask.tsx]()\n\n### Multi-Turn Research Process\n\nThe DeepResearch feature involves multiple iterations of research, each building upon the previous one. The research process includes the following stages:\n\n1.  **Iteration 1:** Research Plan - Outlines the approach to investigating the specific topic.\n2.  **Iterations 2-4:** Research Updates - Dives deeper into complex areas.\n3.  **Final Iteration:** Final Conclusion - Provides a comprehensive answer based on all iterations. Source: [src/components/Ask.tsx]()\n\n### System Prompts\n\nThe `api/websocket_wiki.py` file defines the system prompts used for each iteration of the DeepResearch process. These prompts guide the AI in conducting the research and providing accurate, focused information. Source: [api/websocket_wiki.py]()\n\nThe system prompts vary based on the iteration number:\n\n*   **First Iteration:** Focuses on outlining the research plan. Source: [api/websocket_wiki.py]()\n*   **Intermediate Iterations:** Build upon previous research and explore areas needing further investigation. Source: [api/websocket_wiki.py]()\n*   **Final Iteration:** Synthesizes all previous findings into a comprehensive conclusion. Source: [api/websocket_wiki.py]()\n\n### Research States\n\nThe `Ask` component displays the current research iteration and completion status. It indicates whether the multi-turn research process is enabled, the current iteration number, and whether the research is complete. Source: [src/components/Ask.tsx]()\n\n```tsx\n{deepResearch && (\n  <div className="text-xs text-purple-600 dark:text-purple-400">\n    Multi-turn research process enabled\n    {researchIteration > 0 && !researchComplete && ` (iteration ${researchIteration})`}\n    {researchComplete && ` (complete)`}\n  </div>\n)}\n```\n\nSources: [src/components/Ask.tsx:35-41]()\n\n## MCP Integration\n\nThe Ask and DeepResearch features are integrated with the Model Context Protocol (MCP) via the `mcp-server.py` script. This allows AI assistants like Claude Desktop and Cursor to directly access the repository\'s documentation and analysis capabilities. Source: [mcp/README.md]()\n\n### Available Tools\n\nThe MCP server exposes the following tools:\n\n*   `read_wiki_structure`: Retrieves the complete wiki structure and documentation overview. Source: [mcp/mcp-server.py]()\n*   `read_wiki_contents`: Retrieves detailed documentation content for a specific topic or page. Source: [mcp/mcp-server.py]()\n*   `ask_question`: Asks intelligent questions about the repository using AI-powered analysis. Source: [mcp/mcp-server.py]()\n\n### Architecture\n\n```mermaid\ngraph TD\n    A[AI Assistant] --> B(MCP Server);\n    B --> C{AutoDoc API};\n    C --> D[Repository Data];\n    D --> C;\n    C --> B;\n    B --> A;\n    style A fill:#f9f,stroke:#333,stroke-width:2px\n    style B fill:#ccf,stroke:#333,stroke-width:2px\n    style C fill:#ccf,stroke:#333,stroke-width:2px\n    style D fill:#f9f,stroke:#333,stroke-width:2px\n```\n\nThe AI Assistant interacts with the MCP Server, which in turn communicates with the AutoDoc API to retrieve re',
        'filePaths': ['README.md'],
        'importance': 'medium',
        'relatedPages': ['data-flow', 'project-structure']
    }
}
        
        response = self.test_client.post(
            "/webhook",
            json=self.raw_json,
            headers=self.headers_mock
        )
        self.assertEqual(response.status_code, 202)

    @patch('websockets.connect')
    @patch('api.web_hook.github_api.hmac.compare_digest')
    def test_github_webhook_mocked_ws(self, mock_compare_digest, mock_ws_connect):
        """
        Test Github webhook endpoint with a sample payload.
        """
        mock_compare_digest.return_value = True
        mock_ws = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws
        mock_ws.__aiter__.side_effect = iter([
        """
<wiki_structure>
  <title>AutoDoc Wiki</title>
  <description>Comprehensive documentation for the AutoDoc project, an AI-powered tool that automatically generates interactive wikis for GitHub, GitLab, and Bitbucket repositories.</description>
  <sections>
    <section id="overview">
      <title>Overview</title>
      <pages>
        <page_ref>introduction</page_ref>
        <page_ref>features</page_ref>
        <page_ref>quick_start</page_ref>
      </pages>
    </section>
    <section id="system_architecture">
      <title>System Architecture</title>
      <pages>
        <page_ref>architecture</page_ref>
        <page_ref>data_flow</page_ref>
      </pages>
    </section>
    <section id="core_features">
      <title>Core Features</title>
      <pages>
        <page_ref>ask_feature</page_ref>
        <page_ref>deep_research</page_ref>
      </pages>
    </section>
    <section id="model_integration">
      <title>Model Integration</title>
      <pages>
        <page_ref>model_selection</page_ref>
        <page_ref>openrouter_integration</page_ref>
      </pages>
    </section>
    <section id="deployment_infrastructure">
      <title>Deployment and Infrastructure</title>
      <pages>
        <page_ref>deployment</page_ref>
        <page_ref>configuration</page_ref>
      </pages>
    </section>
  </sections>
  <pages>
    <page id="introduction">
      <title>Introduction</title>
      <description>General introduction to the AutoDoc project, its purpose, and goals.</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>README.md</file_path>
      </relevant_files>
      <related_pages>
        <related>features</related>
        <related>quick_start</related>
      </related_pages>
      <parent_section>overview</parent_section>
    </page>
    <page id="features">
      <title>Features</title>
      <description>Detailed overview of the key features offered by AutoDoc, including instant documentation, private repository support, smart analysis, beautiful diagrams, easy navigation, Ask feature, DeepResearch, multiple model providers, and MCP integration.</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>src/app/[owner]/[repo]/page.tsx</file_path>
      </relevant_files>
      <related_pages>
        <related>introduction</related>
        <related>quick_start</related>
        <related>ask_feature</related>
        <related>deep_research</related>
      </related_pages>
      <parent_section>overview</parent_section>
    </page>
    <page id="quick_start">
      <title>Quick Start</title>
      <description>Instructions on how to quickly get started with AutoDoc using Docker or manual setup.</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>docker-compose.yml</file_path>
        <file_path>Dockerfile</file_path>
      </relevant_files>
      <related_pages>
        <related>introduction</related>
        <related>features</related>
        <related>deployment</related>
      </related_pages>
      <parent_section>overview</parent_section>
    </page>
    <page id="architecture">
      <title>Architecture</title>
      <description>Explanation of the system architecture, including the frontend, backend, and data flow. This page will benefit from a visual diagram.</description>
      <importance>high</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/main.py</file_path>
        <file_path>src/app/[owner]/[repo]/page.tsx</file_path>
      </relevant_files>
      <related_pages>
        <related>data_flow</related>
        <related>model_selection</related>
      </related_pages>
      <parent_section>system_architecture</parent_section>
    </page>
    <page id="data_flow">
      <title>Data Flow</title>
      <description>Detailed description of how data flows through the system, from repository cloning to wiki generation. This page will benefit from a visual diagram.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>api/data_pipeline.py</file_path>
        <file_path>api/rag.py</file_path>
        <file_path>src/app/[owner]/[repo]/page.tsx</file_path>
      </relevant_files>
      <related_pages>
        <related>architecture</related>
        <related>model_selection</related>
      </related_pages>
      <parent_section>system_architecture</parent_section>
    </page>
    <page id="ask_feature">
      <title>Ask Feature</title>
      <description>Explanation of the Ask feature, which allows users to chat with their repository using RAG. Includes information on context-aware responses, real-time streaming, and conversation history.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/simple_chat.py</file_path>
        <file_path>src/components/Ask.tsx</file_path>
      </relevant_files>
      <related_pages>
        <related>deep_research</related>
      </related_pages>
      <parent_section>core_features</parent_section>
    </page>
    <page id="deep_research">
      <title>DeepResearch</title>
      <description>Explanation of the DeepResearch feature, which provides in-depth investigation of complex topics through multiple research iterations.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/rag.py</file_path>
        <file_path>src/components/Ask.tsx</file_path>
      </relevant_files>
      <related_pages>
        <related>ask_feature</related>
      </related_pages>
      <parent_section>core_features</parent_section>
    </page>
    <page id="model_selection">
      <title>Model Selection</title>
      <description>Details on the provider-based model selection system, including supported providers (Google, OpenAI, OpenRouter, Ollama), environment variables, and configuration files.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/config/generator.json</file_path>
        <file_path>api/openai_client.py</file_path>
        <file_path>api/openrouter_client.py</file_path>
        <file_path>api/bedrock_client.py</file_path>
      </relevant_files>
      <related_pages>
        <related>openrouter_integration</related>
      </related_pages>
      <parent_section>model_integration</parent_section>
    </page>
    <page id="openrouter_integration">
      <title>OpenRouter Integration</title>
      <description>How to use OpenRouter as a model provider, including configuration steps and benefits.</description>
      <importance>low</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/openrouter_client.py</file_path>
      </relevant_files>
      <related_pages>
        <related>model_selection</related>
      </related_pages>
      <parent_section>model_integration</parent_section>
    </page>
    <page id="deployment">
      <title>Deployment</title>
      <description>Instructions on how to deploy AutoDoc using Docker, including environment variables and Docker Compose setup.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>docker-compose.yml</file_path>
        <file_path>Dockerfile</file_path>
      </relevant_files>
      <related_pages>
        <related>configuration</related>
      </related_pages>
      <parent_section>deployment_infrastructure</parent_section>
    </page>
    <page id="configuration">
      <title>Configuration</title>
      <description>Details on the various configuration options, including API keys, environment variables, and configuration files. Includes information on logging configuration and authorization mode.</description>
      <importance>medium</importance>
      <relevant_files>
        <file_path>README.md</file_path>
        <file_path>api/config.py</file_path>
        <file_path>api/logging_config.py</file_path>
      </relevant_files>
      <related_pages>
        <related>deployment</related>
      </related_pages>
      <parent_section>deployment_infrastructure</parent_section>
    </page>
  </pages>
</wiki_structure>
"""
        ])
        
        response = self.test_client.post(
            "/webhook",
            json=self.raw_json,
            headers=self.headers_mock
        )
        self.assertEqual(response.status_code, 202)

    @patch('websockets.connect')
    @patch('api.web_hook.github_api.hmac.compare_digest')
    async def test_github_webhook_mocked_ws_1(self, mock_compare_digest, mock_ws_connect):
        """
        Test Github webhook endpoint with a sample payload.
        """
        wiki_structure = WikiStructure(id='wiki', 
                                       title='title', 
                                       description='description', pages=['hello', 'hello'], 
                                       sections=['hello', 'hello'], 
                                       root_sections=['hello', 'hello'])
        generated_pages = {
    'introduction': {
        'id': 'introduction',
        'title': 'Introduction',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [README.md](README.md)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [instructions/features.md](instructions/features.md)\n- [api/openrouter_client.py](api/openrouter_client.py)\n</details>\n\n# Introduction\n\nAutoDoc is a tool designed to automatically generate documentation for software repositories by leveraging AI analysis. It aims to simplify the process of creating and maintaining comprehensive documentation, making it easier for developers to understand, use, and contribute to projects. The tool uses a combination of code analysis and large language models (LLMs) to produce detailed documentation, including API references, architecture overviews, and usage examples.\n\nThe AutoDoc MCP Server acts as a bridge between the auto-generated documentation and AI assistants, enabling users to browse the documentation structure, read detailed content, and ask intelligent questions about the repository using RAG-powered AI. This introduction will provide an overview of AutoDoc\'s features, architecture, and usage, highlighting its benefits for both developers and users.\n\n## Overview of AutoDoc\n\nAutoDoc automates the generation of documentation for software repositories. It analyzes the code, structure, and documentation within a repository to create a comprehensive wiki. This includes page titles and IDs for navigation, importance levels indicating content priority, related pages and cross-references, and file paths that contributed to each documentation page. The generated documentation is designed to help users understand the repository\'s structure, components, and functionality.  The system also supports integration with Model Context Protocol (MCP) for enhanced interaction with AI assistants. [README.md]()\n\n## Key Features\n\nAutoDoc offers several key features that streamline the documentation process:\n\n*   **Automated Documentation Generation:** Automatically generates documentation by analyzing the repository\'s code and structure.\n*   **AI-Powered Content Creation:** Uses AI to create detailed documentation, including API references, architecture overviews, and usage examples.\n*   **Comprehensive Wiki Structure:** Organizes documentation into a structured wiki with page titles, IDs, and cross-references.\n*   **Integration with AI Assistants:** Supports integration with AI assistants through the Model Context Protocol (MCP). [README.md]()\n*   **llms.txt Generation:** Creates an `llms.txt` file to improve LLM interactions with the repository. [instructions/features.md]()\n\n## AutoDoc MCP Server\n\nThe AutoDoc MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) implementation that allows AI assistants to directly access the documentation and analysis capabilities generated by AutoDoc. It provides a bridge between the auto-generated documentation and AI assistants, enabling users to:\n\n*   Browse Documentation Structure\n*   Read Detailed Content\n*   Ask Intelligent Questions using RAG-powered AI [README.md]()\n\n### Available Tools\n\nThe MCP server provides two main tools:\n\n1.  `read_wiki_structure`: Retrieves the complete wiki structure and documentation overview.\n2.  `read_wiki_contents`: Retrieves detailed documentation content for a specific topic or page. [README.md]()\n\n### Using the Tools\n\nTo use these tools, you can send requests to the MCP server with the appropriate parameters. For example, to retrieve the wiki structure, you can use the `read_wiki_structure` tool. To retrieve the content of a specific page, you can use the `read_wiki_contents` tool with the page title or ID as the topic. [mcp/mcp-server.py]()\n\n## llms.txt File Generation\n\nAutoDoc generates an `llms.txt` file to enhance interactions with Large Language Models (LLMs). This file acts as a curated "table of contents" or a high-level summary, pointing the LLM directly to the most important, AI-friendly information. It saves processing time and improves the accuracy of the LLM\'s understanding. [instructions/features.md]()\n\n### Implementation\n\nThe `llms.txt` file is generated dynamically after the main documentation/wiki is created. The file includes:\n\n*   An H1 title with the repository name.\n*   A blockquote summary generated by an LLM call.\n*   H2 sections and links to major topics or pages in the wiki. [instructions/features.md]()\n\n## Conclusion\n\nAutoDoc simplifies the process of creating and maintaining documentation for software repositories. By automating documentation generation and leveraging AI-powered content creation, AutoDoc makes it easier for developers to understand, use, and contribute to projects. The integration with AI assistants through the MCP server further enhances the accessibility and usability of the generated documentation.',
        'filePaths': ['README.md'],
        'importance': 'high',
        'relatedPages': ['quick-start', 'data-flow']
    },
    'quick-start': {
        'id': 'quick-start',
        'title': 'Quick Start',
        'content': '<details>\n<summary>Relevant source files</summary>\n\n- [mcp/README.md](mcp/README.md)\n- [docker-compose.yml](docker-compose.yml)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n- [api/data_pipeline.py](api/data_pipeline.py)\n</details>\n\n# Quick Start\n\nThe AutoDoc MCP Server facilitates interaction with AI assistants by providing access to repository documentation and analysis capabilities generated by AutoDoc. It leverages the Model Context Protocol (MCP) to bridge AutoDoc-generated documentation and AI assistants. This allows users to browse the repository\'s wiki, read detailed content, and ask intelligent questions using RAG-powered AI. The server uses HTTP APIs to communicate with a running AutoDoc instance, ensuring responses are based on the repository\'s code and documentation.  `Sources: [mcp/README.md]()`\n\nThis quick start guide will walk you through setting up and using the AutoDoc MCP Server.\n\n## Prerequisites\n\n*   Docker installed and running.\n*   An AutoDoc instance running and accessible.\n\n## Installation and Setup\n\n1.  **Clone the repository:**\n\n    ```bash\n    git clone <repository_url>\n    cd webhook_autodoc\n    ```\n    (Note: Replace `<repository_url>` with the actual repository URL.)\n2.  **Configure Environment Variables:**\n\n    The MCP server requires certain environment variables to be configured. These can be set directly in your shell or using a `.env` file.\n\n    *   `REPO_URL`: The URL of the repository you want to document.  `Sources: [mcp/mcp-server.py:63,77,130]()`\n    *   `OPENROUTER_API_KEY`: API key for OpenRouter.  `Sources: [api/openrouter_client.py]()`\n    *   `OR_MODEL`: OpenRouter model to use.  `Sources: [api/openrouter_client.py]()`\n\n3.  **Run with Docker Compose:**\n\n    The easiest way to get started is using Docker Compose.  The `docker-compose.yml` file defines the necessary services and configurations.\n\n    ```bash\n    docker-compose up -d\n    ```\n\n    This command builds and starts the MCP server in detached mode.  `Sources: [docker-compose.yml]()`\n\n    The `docker-compose.yml` file sets up the mcp-server service.  `Sources: [docker-compose.yml]()` It defines the image, ports, volumes, and environment variables required to run the server.  `Sources: [docker-compose.yml]()`\n\n    ```yaml\n    version: "3.8"\n    services:\n      mcp-server:\n        image: tiangolo/uvicorn-gunicorn-fastapi:python3.11\n        command: uvicorn mcp.mcp-server:app --host 0.0.0.0 --port 8000 --workers 1\n        volumes:\n          - ./mcp:/app/mcp\n          - ./api:/app/api\n        ports:\n          - "8000:8000"\n        environment:\n          - REPO_URL=${REPO_URL}\n          - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}\n          - OR_MODEL=${OR_MODEL}\n    ```\n    `Sources: [docker-compose.yml]()`\n\n4.  **Verify the Setup:**\n\n    Once the Docker container is running, you can verify that the MCP server is accessible by sending a request to the `/docs` endpoint.\n\n## Available Tools\n\nThe AutoDoc MCP Server provides the following tools:\n\n### 1. `read_wiki_structure`\n\nThis tool retrieves the complete wiki structure and documentation overview for the configured repository.  `Sources: [mcp/README.md]()` It provides an index of all available documentation pages created by AutoDoc\'s AI analysis.  `Sources: [mcp/README.md]()`\n\n**Returns:**\n\n*   Page titles and IDs for navigation.  `Sources: [mcp/README.md]()`\n*   Importance levels (high/medium/low) indicating content priority.  `Sources: [mcp/README.md]()`\n*   Related pages and cross-references.  `Sources: [mcp/README.md]()`\n*   File paths that contributed to each documentation page.  `Sources: [mcp/README.md]()`\n*   Overview of the repository\'s documentation organization.  `Sources: [mcp/README.md]()`\n\n### 2. `read_wiki_contents`\n\nThis tool retrieves detailed documentation content for a specific topic or page from the configured repository.  `Sources: [mcp/README.md]()` It fetches the complete content of a documentation page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/README.md]()` The content is AI-generated based on analysis of the repository\'s code, structure, and documentation.  `Sources: [mcp/README.md]()`\n\n**Parameters:**\n\n*   `topic` (string): The documentation topic to retrieve. Can be either:\n    *   Page title (e.g., "Getting Started", "API Reference")  `Sources: [mcp/README.md]()`\n    *   Page ID (e.g., "page-1", "page-2")  `Sources: [mcp/README.md]()`\n\n**Topic Identification Methods:**\n\n*   **Page titles**: Use exact titles like "Getting Started", "API Documentation", "Features Overview".  `Sources: [mcp/README.md]()`\n*   **Page IDs**: Use identifiers like "page-1", "page-2", etc.  `Sources: [mcp/README.md]()`\n*   **Case-insensitive matching**: Both "getting started" and "Getting Started" work.  `Sources: [mcp/README.md]()`\n\n## Usage Examples\n\nThe `read_wiki_structure` and `read_wiki_contents` tools can be accessed via HTTP requests to the MCP server.  The `read_wiki_structure` tool retrieves the wiki structure.  `Sources: [mcp/mcp-server.py]()` The `read_wiki_contents` tool retrieves the content of a specific topic.  `Sources: [mcp/mcp-server.py]()`\n\n### Example: Retrieving Wiki Structure\n\n```python\nimport requests\n\nurl = "http://localhost:8000/read_wiki_structure"  # Replace with your server\'s address\nparams = {"repo_url": "[https://github.com/Taha-1005/webhook_autodoc](https://github.com/Taha-1005/webhook_autodoc)"}  # Replace with your repo URL\n\nresponse = requests.get(url, params=params)\n\nif response.status_code == 200:\n    data = response.json()\n    print(data)\nelse:\n    print(f"Error: {response.status_code} - {response.text}")\n```\n\n### Example: Retrieving Wiki Contents\n\n```python\nimport requests\n\nurl = "http://localhost:8000/read_wiki_contents"  # Replace with your server\'s address\nparams = {\n    "repo_url": "[https://github.com/Taha-1005/webhook_autodoc](https://github.com/Taha-1005/webhook_autodoc)",  # Replace with your repo URL\n    "topic": "Quick Start"  # Replace with the desired topic\n}\n\nresponse = requests.get(url, params=params)\n\nif response.status_code == 200:\n    data = response.json()\n    print(data)\nelse:\n    print(f"Error: {response.status_code} - {response.text}")\n```\n\n## Conclusion\n\nThis guide provided a quick start to setting up and using the AutoDoc MCP Server. By following these steps, you can easily integrate your AutoDoc-generated documentation with AI assistants, enabling powerful new ways to interact with your repository\'s knowledge.',
        'filePaths': ['README.md', 'docker-compose.yml'],
        'importance': 'high',
        'relatedPages': ['introduction', 'docker-setup']
    },
    'data-flow': {
        'id': 'data-flow',
        'title': 'Data Flow',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [api/data_pipeline.py](api/data_pipeline.py)\n- [api/rag.py](api/rag.py)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [README.md](README.md)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n</details>\n\n# Data Flow\n\nThis page outlines the data flow within the AutoDoc project, focusing on how data is processed from repository analysis to providing documentation and answering user queries. It covers the key components involved in data ingestion, processing, and retrieval, highlighting the roles of different modules and APIs. The data flow includes repository analysis, wiki structure determination, content generation, and serving documentation via the MCP server.\n\n## Repository Analysis and Wiki Generation\n\nThe data flow begins with the analysis of a repository to determine its structure and generate documentation. This process is initiated by the `determineWikiStructure` function in `src/app/[owner]/[repo]/page.tsx`. This function orchestrates the analysis of the repository\'s file tree and README content to create a wiki structure. The determined structure is then used to generate individual wiki pages. The overall process involves several steps:\n\n1.  **Repository Information Gathering:** The `determineWikiStructure` function first gathers repository information, including the owner and repository name, to construct the repository URL. It then prepares a request body containing the repository URL, repository type, and a prompt for the AI model to analyze the repository and create a wiki structure.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n2.  **Wiki Structure Determination:** The request is sent to the backend, where the AI model analyzes the file tree and README content to determine a logical wiki structure. The AI model suggests pages, sections, and their relationships based on the repository\'s content.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n3.  **Content Generation:** Once the wiki structure is determined, the system generates content for each page, incorporating code snippets, diagrams, and explanations extracted from the repository.  `Sources: [api/data_pipeline.py](), [api/rag.py]()`\n\n```mermaid\ngraph TD\n    A[Repository File Tree & README] --> B(determineWikiStructure);\n    B --> C{AI Model};\n    C --> D[Wiki Structure (pages, sections)];\n    D --> E(Content Generation);\n    E --> F[Wiki Pages (Markdown)];\n```\n\nThis diagram illustrates the initial steps of the data flow, from gathering repository information to generating wiki pages. The `determineWikiStructure` function plays a central role in initiating this process.\n\n## Serving Documentation via MCP Server\n\nThe AutoDoc MCP Server facilitates access to the generated documentation via AI assistants. The server implements the Model Context Protocol (MCP) to provide a seamless bridge between the generated documentation and AI assistants like Claude Desktop and Cursor.  `Sources: [mcp/README.md]()`\n\n### MCP Server Tools\n\nThe MCP server provides several tools for accessing the documentation:\n\n1.  **`read_wiki_structure`:** This tool retrieves the complete wiki structure and documentation overview for the configured repository. It provides an index of all available documentation pages, including titles, IDs, importance levels, and related pages.  `Sources: [mcp/mcp-server.py](), [mcp/README.md]()`\n2.  **`read_wiki_contents`:** This tool retrieves detailed documentation content for a specific topic or page from the configured repository. It fetches the complete content of a documentation page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/mcp-server.py](), [mcp/README.md]()`\n\n### Data Flow within MCP Server\n\nThe data flow within the MCP server involves receiving requests from AI assistants, retrieving the requested documentation content, and returning the content to the AI assistant.\n\n```mermaid\nsequenceDiagram\n    participant AI Assistant\n    participant MCP Server\n    participant Data Store\n\n    AI Assistant->>MCP Server: Request documentation (topic/page ID)\n    activate MCP Server\n    MCP Server->>Data Store: Retrieve documentation content\n    activate Data Store\n    Data Store-->>MCP Server: Documentation content\n    deactivate Data Store\n    MCP Server-->>AI Assistant: Documentation content\n    deactivate MCP Server\n```\n\nThis sequence diagram illustrates the data flow within the MCP server, from receiving requests from AI assistants to retrieving and returning documentation content. The MCP server acts as an intermediary between the AI assistant and the data store.\n\n### Code Snippet: `read_wiki_contents`\n\n```python\n@mcp.tool\nasync def read_wiki_contents(topic: str, repo_url: str = REPO_URL) -> Dict[str, Any]:\n    """\n    Retrieve detailed documentation content for a specific topic or page from the configured repository.\n    """\n    # Implementation details for retrieving documentation content\n    pass\n```\n\nThis code snippet shows the `read_wiki_contents` tool in the MCP server, which retrieves detailed documentation content for a specific topic or page.  `Sources: [mcp/mcp-server.py]()`\n\n## RAG-Powered AI for Answering Questions\n\nThe project utilizes Retrieval-Augmented Generation (RAG) to answer user questions based on the repository\'s documentation. The RAG pipeline involves retrieving relevant documents based on the user\'s query and generating an answer using an AI model.  `Sources: [api/rag.py]()`\n\n### RAG Pipeline Steps\n\n1.  **User Query:** The user submits a question or query related to the repository.\n2.  **Document Retrieval:** The RAG system retrieves relevant documents from the documentation based on the user\'s query. This involves embedding the query and documents and finding the documents with the most similar embeddings.  `Sources: [api/rag.py]()`\n3.  **Answer Generation:** The AI model generates an answer based on the retrieved documents and the user\'s query. This involves feeding the query and retrieved documents to the AI model and generating a coherent and informative answer.  `Sources: [api/rag.py]()`\n\n### Data Flow Diagram for RAG\n\n```mermaid\ngraph TD\n    A[User Query] --> B(Document Retrieval);\n    B --> C{AI Model};\n    C --> D[Generated Answer];\n```\n\nThis diagram illustrates the data flow in the RAG pipeline, from the user query to the generated answer. The document retrieval and AI model components play key roles in this process.\n\n## Conclusion\n\nThe data flow within the AutoDoc project encompasses repository analysis, wiki generation, serving documentation via the MCP server, and answering user queries using RAG. The project leverages AI models and various modules to process data and provide comprehensive documentation and answers. Understanding the data flow is crucial for developers working on or learning about the project, as it provides insights into the system\'s architecture and functionality.',
        'filePaths': ['README.md', 'api/rag.py', 'api/data_pipeline.py'],
        'importance': 'medium',
        'relatedPages': ['project-structure', 'ask-deepresearch']
    },
    'project-structure': {
        'id': 'project-structure',
        'title': 'Project Structure',
        'content': "<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [src/app/[owner]/[repo]/page.tsx](src/app/[owner]/[repo]/page.tsx)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [api/openrouter_client.py](api/openrouter_client.py)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [mcp/README.md](mcp/README.md)\n- [src/app/[owner]/[repo]/slides/page.tsx](src/app/[owner]/[repo]/slides/page.tsx)\n- [instructions/features.md](instructions/features.md)\n</details>\n\n# Project Structure\n\nThis document provides an overview of the project structure, focusing on key components and their relationships. It covers the client-side application structure, the Model Context Protocol (MCP) server, API endpoints, and supporting files that contribute to the project's functionality. This structure enables AI assistants to access repository documentation and analysis capabilities.\n\n## Client-Side Application Structure\n\nThe client-side application is primarily located in the `src/app` directory. The `[owner]/[repo]` directory structure suggests a dynamic routing system based on the repository owner and name. Key files include `page.tsx` and `slides/page.tsx`.\n\n### `page.tsx`\n\nThis file appears to be the main page component for displaying the wiki content. It fetches and displays the wiki structure and generated pages. It uses `getRepoUrl` to construct the repository URL and interacts with the backend to determine the wiki structure using the `determineWikiStructure` function. This function takes the file tree and README content as input to create a logical wiki structure. It also handles loading states and error conditions.  `Sources: [src/app/[owner]/[repo]/page.tsx]()`\n\n### `slides/page.tsx`\n\nThis file is responsible for generating slide content from the wiki data. It retrieves wiki data and structures it into slides, prioritizing high-importance pages. It limits the total content length to avoid token limits.  `Sources: [src/app/[owner]/[repo]/slides/page.tsx]()`\n\n## Model Context Protocol (MCP) Server\n\nThe MCP server, implemented in `mcp/mcp-server.py`, acts as a bridge between the AutoDoc-generated documentation and AI assistants. It is built using FastMCP and allows AI assistants to browse documentation structure, read detailed content, and ask intelligent questions.  `Sources: [mcp/README.md]()`\n\n### Available Tools\n\nThe MCP server provides two main tools: `read_wiki_structure` and `read_wiki_contents`.  `Sources: [mcp/README.md]()`\n\n1.  **`read_wiki_structure`**: This tool retrieves the complete wiki structure and documentation overview for the configured repository. It provides page titles, IDs, importance levels, related pages, and file paths.  `Sources: [mcp/README.md]()`\n2.  **`read_wiki_contents`**: This tool retrieves detailed documentation content for a specific topic or page, including markdown text, code examples, diagrams, and metadata.  `Sources: [mcp/README.md]()`\n\n### Key Functions\n\n*   **`read_wiki_structure(repo_url: str = REPO_URL)`**: Retrieves the wiki structure.  `Sources: [mcp/mcp-server.py]()`\n*   **`read_wiki_contents(topic: str, repo_url: str = REPO_URL)`**: Retrieves detailed documentation content for a specific topic.  `Sources: [mcp/mcp-server.py]()`\n\n## API Endpoints\n\nThe project includes API endpoints for interacting with external services and handling requests.\n\n### `api/openrouter_client.py`\n\nThis file likely contains the implementation for interacting with the OpenRouter API.  The content of this file was not available in the provided documents.\n\n### `api/websocket_wiki.py`\n\nThis file seems to handle WebSocket communication for wiki-related functionalities. It defines system prompts for different stages of a deep research process. These prompts guide the AI in analyzing the repository and generating documentation.  `Sources: [api/websocket_wiki.py]()`\n\n#### System Prompts\n\nThe system prompts are designed for multi-turn deep research, focusing on specific topics within the repository. The prompts vary based on the research iteration and whether it's the final iteration. They instruct the AI to provide detailed, focused information, synthesize findings, and maintain continuity with previous research.  `Sources: [api/websocket_wiki.py]()`\n\n## Supporting Files\n\nSeveral supporting files contribute to the project's overall structure and functionality.\n\n### `instructions/features.md`\n\nThis file outlines the implementation plan for various features, including the dynamic generation of an `llms.txt` file. This file acts as a curated table of contents, pointing LLMs to the most important, AI-friendly information.  `Sources: [instructions/features.md]()`\n\n### `llms.txt`\n\nThe `llms.txt` file, dynamically generated, contains a summary of the project and links to key modules and documentation pages. It improves the accuracy and efficiency of LLM interactions with the repository.  `Sources: [instructions/features.md]()`\n\n## Architecture Diagram\n\n```mermaid\ngraph TD\n    A[Client-Side Application] --> B(page.tsx);\n    A --> C(slides/page.tsx);\n    B --> D{Determine Wiki Structure};\n    D --> E[File Tree & README];\n    E --> F(Backend API);\n    F --> G(mcp/mcp-server.py);\n    G --> H{read_wiki_structure};\n    G --> I{read_wiki_contents};\n    I --> J[Documentation Content];\n    H --> K[Wiki Structure];\n    style A fill:#f9f,stroke:#333,stroke-width:2px\n    style G fill:#ccf,stroke:#333,stroke-width:2px\n```\n\nThis diagram illustrates the high-level architecture, showing the interaction between the client-side application, backend API, and MCP server.  `Sources: [src/app/[owner]/[repo]/page.tsx](), [mcp/mcp-server.py]()`\n\n## Conclusion\n\nThe project structure is designed to facilitate AI-driven documentation and analysis of code repositories. The client-side application provides a user interface for Browse the generated wiki, while the MCP server enables AI assistants to access detailed documentation content. The API endpoints and supporting files ensure seamless integration and efficient interaction with external services.",
        'filePaths': ['README.md'],
        'importance': 'medium',
        'relatedPages': ['api-server', 'mcp-server']
    },
    'ask-deepresearch': {
        'id': 'ask-deepresearch',
        'title': 'Ask & DeepResearch Features',
        'content': '<details>\n<summary>Relevant source files</summary>\n\nThe following files were used as context for generating this wiki page:\n\n- [README.md](README.md)\n- [src/components/Ask.tsx](src/components/Ask.tsx)\n- [api/websocket_wiki.py](api/websocket_wiki.py)\n- [mcp/mcp-server.py](mcp/mcp-server.py)\n- [mcp/README.md](mcp/README.md)\n</details>\n\n# Ask & DeepResearch Features\n\nThe Ask and DeepResearch features in this project provide users with the ability to interact with the repository\'s documentation and code through natural language queries. The Ask feature delivers context-aware responses using Retrieval Augmented Generation (RAG), while DeepResearch conducts multi-turn investigations to provide comprehensive answers to complex questions. These features enhance the accessibility and understanding of the codebase, making it easier for users to learn, contribute, and troubleshoot.\n\n## Ask Feature\n\nThe Ask feature allows users to pose questions about the repository and receive answers grounded in the actual code. It leverages Retrieval Augmented Generation (RAG) to provide context-aware responses. The system retrieves relevant code snippets to provide grounded responses. Responses are generated in real-time, providing an interactive experience. Source: [README.md]()\n\n### RAG-Powered Responses\n\nThe Ask feature uses Retrieval Augmented Generation (RAG) to generate responses based on the repository\'s content. The AI assistant uses a knowledge base constrained by the analyzed repository content and cannot answer questions about external topics or general programming. If information isn\'t available, the assistant will clearly state this. Source: [mcp/mcp-server.py]()\n\n### Usage\n\nThe `ask_question` tool in `mcp-server.py` provides the RAG functionality. It takes a question as input and returns a detailed answer in markdown format, including code examples, architecture explanations, and usage instructions. Source: [mcp/mcp-server.py]()\n\nExample questions that work well include:\n\n- "How does authentication work in this project?"\n- "What is the main entry point and how does the application start?"\n- "What API endpoints are available and what do they do?"\n- "How is the database schema structured?"\n- "What are the main components and how do they interact?"\n- "How do I set up the development environment?"\n- "What testing frameworks and strategies are used?"\n- "How is error handling implemented?" Source: [mcp/mcp-server.py]()\n\n### Ask Component\n\nThe `Ask` component in `src/components/Ask.tsx` provides the user interface for the Ask feature. It includes a form for submitting questions and displays the AI-generated response. Source: [src/components/Ask.tsx]()\n\n## DeepResearch Feature\n\nThe DeepResearch feature conducts multi-turn investigations to provide comprehensive answers to complex questions. It is enabled by checking the "Deep Research" option in the UI. When enabled, the AI automatically continues research until complete (up to 5 iterations). Source: [src/components/Ask.tsx]()\n\n### Multi-Turn Research Process\n\nThe DeepResearch feature involves multiple iterations of research, each building upon the previous one. The research process includes the following stages:\n\n1.  **Iteration 1:** Research Plan - Outlines the approach to investigating the specific topic.\n2.  **Iterations 2-4:** Research Updates - Dives deeper into complex areas.\n3.  **Final Iteration:** Final Conclusion - Provides a comprehensive answer based on all iterations. Source: [src/components/Ask.tsx]()\n\n### System Prompts\n\nThe `api/websocket_wiki.py` file defines the system prompts used for each iteration of the DeepResearch process. These prompts guide the AI in conducting the research and providing accurate, focused information. Source: [api/websocket_wiki.py]()\n\nThe system prompts vary based on the iteration number:\n\n*   **First Iteration:** Focuses on outlining the research plan. Source: [api/websocket_wiki.py]()\n*   **Intermediate Iterations:** Build upon previous research and explore areas needing further investigation. Source: [api/websocket_wiki.py]()\n*   **Final Iteration:** Synthesizes all previous findings into a comprehensive conclusion. Source: [api/websocket_wiki.py]()\n\n### Research States\n\nThe `Ask` component displays the current research iteration and completion status. It indicates whether the multi-turn research process is enabled, the current iteration number, and whether the research is complete. Source: [src/components/Ask.tsx]()\n\n```tsx\n{deepResearch && (\n  <div className="text-xs text-purple-600 dark:text-purple-400">\n    Multi-turn research process enabled\n    {researchIteration > 0 && !researchComplete && ` (iteration ${researchIteration})`}\n    {researchComplete && ` (complete)`}\n  </div>\n)}\n```\n\nSources: [src/components/Ask.tsx:35-41]()\n\n## MCP Integration\n\nThe Ask and DeepResearch features are integrated with the Model Context Protocol (MCP) via the `mcp-server.py` script. This allows AI assistants like Claude Desktop and Cursor to directly access the repository\'s documentation and analysis capabilities. Source: [mcp/README.md]()\n\n### Available Tools\n\nThe MCP server exposes the following tools:\n\n*   `read_wiki_structure`: Retrieves the complete wiki structure and documentation overview. Source: [mcp/mcp-server.py]()\n*   `read_wiki_contents`: Retrieves detailed documentation content for a specific topic or page. Source: [mcp/mcp-server.py]()\n*   `ask_question`: Asks intelligent questions about the repository using AI-powered analysis. Source: [mcp/mcp-server.py]()\n\n### Architecture\n\n```mermaid\ngraph TD\n    A[AI Assistant] --> B(MCP Server);\n    B --> C{AutoDoc API};\n    C --> D[Repository Data];\n    D --> C;\n    C --> B;\n    B --> A;\n    style A fill:#f9f,stroke:#333,stroke-width:2px\n    style B fill:#ccf,stroke:#333,stroke-width:2px\n    style C fill:#ccf,stroke:#333,stroke-width:2px\n    style D fill:#f9f,stroke:#333,stroke-width:2px\n```\n\nThe AI Assistant interacts with the MCP Server, which in turn communicates with the AutoDoc API to retrieve re',
        'filePaths': ['README.md'],
        'importance': 'medium',
        'relatedPages': ['data-flow', 'project-structure']
    }
}
        repo = 'repo'
        repo_url = 'https://github.com/owner/repo'

        response = await export_wiki_python(wiki_structure, generated_pages, repo, repo_url)

if __name__ == '__main__':
    unittest.main()

