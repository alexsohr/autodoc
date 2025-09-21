import pytest
import json
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.web_hook.app import app

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_github_event():
    return {
        "number": 1,
        "action": "closed",
        "pull_request": {
            "merged": True,
            "base": {
                "ref": "main"
            }
        },
        "repository": {
            "id": 1001069502,
            "full_name": "test-owner/test-repo",
            "private": False,
            "owner": {
                "login": "test-owner",
                "id": 12345
            },
            "html_url": "https://github.com/test-owner/test-repo",
            "default_branch": "main"
        }
    }

@pytest.fixture
def mock_headers():
    return {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": "sha256=mock_signature"
    }

@pytest.mark.asyncio
async def test_github_webhook_end_to_end(test_client, mock_github_event, mock_headers):
    # Mock the HMAC signature verification
    with patch('api.web_hook.app.hmac.compare_digest', return_value=True):
        # Mock the generate_wiki_for_repository function
        with patch('api.web_hook.app.generate_wiki_for_repository') as mock_process:
            mock_process.return_value = {
                "wiki_structure": {
                    "title": "Test Wiki",
                    "description": "Test Description",
                    "pages": [{"id": "test-page", "title": "Test Page"}]
                },
                "generated_pages": {
                    "test-page": {
                        "id": "test-page",
                        "title": "Test Page",
                        "content": "Test content"
                    }
                },
                "repo_url": "https://github.com/test-owner/test-repo"
            }
            
            # Set environment variable for webhook secret
            os.environ["Github_WEBHOOK_SECRET"] = "test_secret"
            
            # Make the request to the webhook endpoint
            response = test_client.post(
                "/webhook",
                json=mock_github_event,
                headers=mock_headers
            )
            
            # Verify the response
            assert response.status_code == 202
            assert "Webhook received" in response.json()["message"]
            
            # Verify the background task was added
            mock_process.assert_called_once()