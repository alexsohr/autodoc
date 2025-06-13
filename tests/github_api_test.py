import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.web_hook.github_api import process_github_repository_async
from api.web_hook.github_api import app
import hmac


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
            }
        }
        self.headers_mock = {
            "X-Hub-Signature": "sha256=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "Content-Type": "application/json",
            "X-GitHub-Event": "push"
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
    def test_github_webhook_mocked_ws(self, mock_compare_digest, mock_ws_connect):
        """
        Test Github webhook endpoint with a sample payload.
        """
        mock_compare_digest.return_value = True
        mock_ws = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws
        mock_ws.__aiter__.return_value = iter([
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

if __name__ == '__main__':
    unittest.main()

