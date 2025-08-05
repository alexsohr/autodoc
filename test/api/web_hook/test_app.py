import pytest
import json
import hmac
import hashlib
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, BackgroundTasks
from fastapi.testclient import TestClient
from api.web_hook.app import app, github_webhook
from api.web_hook.models.github_events import GithubPushEvent


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload for pull request closed event."""
    return {
        "action": "closed",
        "number": 123,
        "pull_request": {
            "merged": True,
            "base": {
                "ref": "main"
            }
        },
        "repository": {
            "id": 123456789,
            "full_name": "octocat/Hello-World",
            "owner": {
                "login": "octocat",
                "id": 1
            },
            "html_url": "https://github.com/octocat/Hello-World",
            "default_branch": "main"
        }
    }


def generate_signature(payload_dict, secret="test_secret"):
    """Generate a valid HMAC signature for a given payload."""
    payload_bytes = json.dumps(payload_dict, separators=(',', ':')).encode('utf-8')
    hash_object = hmac.new(secret.encode('utf-8'), msg=payload_bytes, digestmod=hashlib.sha256)
    return "sha256=" + hash_object.hexdigest(), payload_bytes


class TestGithubWebhook:
    """Test cases for the github_webhook function."""

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    @patch("api.web_hook.app.generate_wiki_for_repository")
    async def test_github_webhook_valid_pull_request_merged(self, mock_generate_wiki, sample_webhook_payload):
        """
        Tests github_webhook with a valid merged pull request to main branch.
        Should process the webhook and add background task.
        """
        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(sample_webhook_payload)

        # Create mock request
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        # Create mock background tasks
        mock_background_tasks = Mock(spec=BackgroundTasks)

        # Call the function
        response = await github_webhook(mock_request, mock_background_tasks)

        # Assertions
        assert response.status_code == 202
        assert "Processing repository octocat/Hello-World in background" in response.body.decode()
        mock_background_tasks.add_task.assert_called_once()

        # Verify the background task was called with correct parameters
        call_args = mock_background_tasks.add_task.call_args
        assert call_args[0][0] == mock_generate_wiki
        assert isinstance(call_args[1]["github_event"], GithubPushEvent)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_missing_signature(self, sample_webhook_payload):
        """
        Tests github_webhook when HMAC signature is missing from headers.
        Should raise HTTPException with 400 status code.
        """
        # Create mock request without signature
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=json.dumps(sample_webhook_payload, separators=(',', ':')).encode('utf-8'))

        # Create a proper mock headers object
        mock_headers = Mock()
        mock_headers.get = Mock(side_effect=lambda key, default=None: {
            "X-GitHub-Event": "pull_request"
        }.get(key, default))
        mock_request.headers = mock_headers

        mock_background_tasks = Mock(spec=BackgroundTasks)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)

        assert exc_info.value.status_code == 400
        assert "Missing HMAC-SHA256 signature" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": ""})
    async def test_github_webhook_missing_webhook_secret(self, sample_webhook_payload):
        """
        Tests github_webhook when webhook secret is not configured in environment.
        Should raise HTTPException with 500 status code.
        """
        # Create mock request
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=json.dumps(sample_webhook_payload).encode('utf-8'))
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_signature"
        }
        
        mock_background_tasks = Mock(spec=BackgroundTasks)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)
        
        assert exc_info.value.status_code == 500
        assert "Webhook secret not configured" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_invalid_signature(self, sample_webhook_payload):
        """
        Tests github_webhook with invalid HMAC signature.
        Should raise HTTPException with 403 status code.
        """
        # Create mock request with invalid signature
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=json.dumps(sample_webhook_payload).encode('utf-8'))
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_signature_hash"
        }
        
        mock_background_tasks = Mock(spec=BackgroundTasks)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)
        
        assert exc_info.value.status_code == 403
        assert "Request signatures didn't match" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_pull_request_not_merged(self):
        """
        Tests github_webhook with pull request closed but not merged.
        Should acknowledge but not process the webhook.
        """
        payload = {
            "action": "closed",
            "number": 123,
            "pull_request": {
                "merged": False,  # Not merged
                "base": {"ref": "main"}
            },
            "repository": {
                "id": 123456789,
                "full_name": "octocat/Hello-World",
                "owner": {"login": "octocat", "id": 1},
                "html_url": "https://github.com/octocat/Hello-World",
                "default_branch": "main"
            }
        }

        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        assert response.status_code == 202
        assert "event type or action is not configured for processing" in response.body.decode()
        mock_background_tasks.add_task.assert_not_called()

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_pull_request_different_branch(self):
        """
        Tests github_webhook with pull request merged to non-default branch.
        Should acknowledge but not process the webhook.
        """
        payload = {
            "action": "closed",
            "number": 123,
            "pull_request": {
                "merged": True,
                "base": {"ref": "develop"}  # Different from default branch
            },
            "repository": {
                "id": 123456789,
                "full_name": "octocat/Hello-World",
                "owner": {"login": "octocat", "id": 1},
                "html_url": "https://github.com/octocat/Hello-World",
                "default_branch": "main"
            }
        }

        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        assert response.status_code == 202
        assert "event type or action is not configured for processing" in response.body.decode()
        mock_background_tasks.add_task.assert_not_called()

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_different_event_type(self, sample_webhook_payload):
        """
        Tests github_webhook with different GitHub event type (not pull_request).
        Should acknowledge but not process the webhook.
        """
        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(sample_webhook_payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "push",  # Different event type
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        assert response.status_code == 202
        assert "event type or action is not configured for processing" in response.body.decode()
        mock_background_tasks.add_task.assert_not_called()

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_different_action(self):
        """
        Tests github_webhook with different action (not closed).
        Should acknowledge but not process the webhook.
        """
        payload = {
            "action": "opened",  # Different action
            "number": 123,
            "pull_request": {
                "merged": False,
                "base": {"ref": "main"}
            },
            "repository": {
                "id": 123456789,
                "full_name": "octocat/Hello-World",
                "owner": {"login": "octocat", "id": 1},
                "html_url": "https://github.com/octocat/Hello-World",
                "default_branch": "main"
            }
        }

        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        assert response.status_code == 202
        assert "event type or action is not configured for processing" in response.body.decode()
        mock_background_tasks.add_task.assert_not_called()

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_invalid_json(self):
        """
        Tests github_webhook with invalid JSON payload.
        Should raise HTTPException with 400 status code.
        """
        # Generate signature for invalid json
        invalid_json = b"invalid json"
        hash_object = hmac.new("test_secret".encode('utf-8'), msg=invalid_json, digestmod=hashlib.sha256)
        signature = "sha256=" + hash_object.hexdigest()

        mock_request = Mock()
        mock_request.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        mock_request.body = AsyncMock(return_value=invalid_json)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)

        assert exc_info.value.status_code == 400
        assert "Invalid JSON in webhook payload" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    @patch("api.web_hook.app.GithubPushEvent")
    async def test_github_webhook_pydantic_validation_error(self, mock_github_event, sample_webhook_payload):
        """
        Tests github_webhook when Pydantic model validation fails.
        Should raise HTTPException with 500 status code.
        """
        # Mock Pydantic validation error
        mock_github_event.side_effect = ValueError("Validation error")

        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(sample_webhook_payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_missing_github_event_header(self, sample_webhook_payload):
        """
        Tests github_webhook when X-GitHub-Event header is missing.
        Should still process if other conditions are met.
        """
        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(sample_webhook_payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)

        # Create a proper mock headers object
        mock_headers = Mock()
        mock_headers.get = Mock(side_effect=lambda key, default=None: {
            "X-Hub-Signature-256": signature
        }.get(key, default))
        mock_request.headers = mock_headers

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        # Should acknowledge but not process since github_event_type will be None
        assert response.status_code == 202
        assert "event type or action is not configured for processing" in response.body.decode()

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_empty_payload(self):
        """
        Tests github_webhook with empty payload.
        Should raise HTTPException due to missing required fields.
        """
        empty_payload = {}

        # Generate valid signature for empty payload
        signature, payload_bytes = generate_signature(empty_payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=empty_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request, mock_background_tasks)

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    async def test_github_webhook_background_task_exception(self, sample_webhook_payload):
        """
        Tests github_webhook when background task addition succeeds.
        The actual background task execution is tested separately.
        """
        # Generate valid signature for this specific payload
        signature, payload_bytes = generate_signature(sample_webhook_payload)

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value=sample_webhook_payload)
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature
        }

        mock_background_tasks = Mock(spec=BackgroundTasks)

        response = await github_webhook(mock_request, mock_background_tasks)

        # Should successfully add background task
        assert response.status_code == 202
        mock_background_tasks.add_task.assert_called_once()


# Integration tests using TestClient
class TestGithubWebhookIntegration:
    """Integration tests for the github_webhook endpoint using TestClient."""

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_endpoint_integration(self, client, sample_webhook_payload):
        """
        Integration test for the /webhook endpoint with valid payload.
        Tests the complete request flow through FastAPI.
        """
        # Generate valid signature using the same method as the helper function
        signature, _ = generate_signature(sample_webhook_payload)

        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json"
        }

        response = client.post("/webhook", json=sample_webhook_payload, headers=headers)

        assert response.status_code == 202
        assert "Processing repository octocat/Hello-World in background" in response.text

    @patch.dict(os.environ, {"Github_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_endpoint_invalid_signature_integration(self, client, sample_webhook_payload):
        """
        Integration test for the /webhook endpoint with invalid signature.
        """
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_signature",
            "Content-Type": "application/json"
        }

        response = client.post("/webhook", json=sample_webhook_payload, headers=headers)

        assert response.status_code == 403
        assert "Request signatures didn't match" in response.text
