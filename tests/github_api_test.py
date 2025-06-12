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
            "action": "closed",
            "number": 1,
            "repository" : {
                "id": 1296269,
                "full_name": "octocat/Hello-World",
                "owner": {
                "login": "octocat",
                "id": 1,
                },
            },
            "sender": {
                "login": "octocat",
                "id": 1,
            }
        }
        self.headers_mock = {
            "X-Hub-Signature": "sha256=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "Content-Type": "application/json"
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
            "/webhook/github",
            json=self.raw_json,
            headers=self.headers_mock
        )
        self.assertEqual(response.status_code, 202)
        self.assertIn("Webhook processed successfully", response.text)

if __name__ == '__main__':
    unittest.main()

