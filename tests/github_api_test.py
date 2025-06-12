import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.web_hook.github_api import process_bitbucket_repository_async, BitbucketPushEvent
from api.api import app
import hmac


class TestGitHubAPI(unittest.TestCase):
    """
    Test suite for Bitbucket API functionality.
    """
    def setUp(self):
        """
        Set up test environment before each test.
        """
        self.test_client = TestClient(app)
        # self.sample_repository = BitbucketPushEvent(
        #     name="test-repo",
        #     full_name="test-owner/test-repo",
        #     owner={"username": "test-owner"},
        #     scm="git",
        #     is_private=False
        # )
        self.raw_json = {
            "eventKey": "repo:refs_changed",
            "date": "2017-09-19T09:45:32+1000",
            "actor": {
                "name": "admin",
                "emailAddress": "admin@example.com",
                "id": 1,
                "displayName": "Administrator",
                "active": True,
                "slug": "admin",
                "type": "NORMAL"
            },
            "repository": {
                "slug": "repository",
                "id": 84,
                "name": "repository",
                "scmId": "git",
                "state": "AVAILABLE",
                "statusMessage": "Available",
                "forkable": True,
                "project": {
                    "key": "PROJ",
                    "id": 84,
                    "name": "project",
                    "public": False,
                    "type": "NORMAL"
                },
                "public": False
            },
            "changes": [
                {
                    "ref": {
                        "id": "refs/heads/master",
                        "displayId": "master",
                        "type": "BRANCH"
                    },
                    "refId": "refs/heads/master",
                    "fromHash": "ecddabb624f6f5ba43816f5926e580a5f680a932",
                    "toHash": "178864a7d521b6f5e720b386b2c2b0ef8563e0dc",
                    "type": "UPDATE"
                }
            ]
        }
        self.headers_mock = {
            "X-Hub-Signature": "sha256=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "Content-Type": "application/json"
        }
        # Environmental setup for testing
        os.environ["SERVER_BASE_URL"] = "http://localhost:8001"

    @patch('api.web_hook.github_api.hmac.compare_digest')
    def test_bitbucket_webhook(self, mock_compare_digest):
        """
        Test Bitbucket webhook endpoint with a sample payload.
        """
        mock_compare_digest.return_value = True
        response = self.test_client.post(
            "/webhook/bitbucket",
            json=self.raw_json,
            headers=self.headers_mock
        )
        self.assertEqual(response.status_code, 202)
        self.assertIn("Webhook processed successfully", response.text)

#     def test_bitbucket_repository_model(self):
#         """
#         Test BitbucketRepository model initialization.
#         """
#         repo = self.sample_repository
#         self.assertEqual(repo.name, "test-repo")
#         self.assertEqual(repo.full_name, "test-owner/test-repo")
#         self.assertEqual(repo.owner["username"], "test-owner")

#     @patch('api.bitbucket_api.get_repo_file_tree')
#     @patch('api.bitbucket_api.get_repo_readme')
#     @patch('api.bitbucket_api.call_websocket_chat')
#     async def test_process_bitbucket_repository_websocket_call(self, mock_websocket, mock_get_readme, mock_get_file_tree):
#         """
#         Test that process_bitbucket_repository_async calls the WebSocket with correct parameters.
#         """
#         # Setup mocks
#         mock_get_file_tree.return_value = "file1.py\nfile2.py\nREADME.md"
#         mock_get_readme.return_value = "# Test Repository\nThis is a test repository."
#         mock_websocket.return_value = "Success response"
#         # Call the function to test
#         result = await process_bitbucket_repository_async(self.sample_repository, "test-user")
#         # Verify WebSocket was called with the correct parameters
#         mock_websocket.assert_called_once()
#         call_args = mock_websocket.call_args[1]['request_body']
#         # Verify the WebSocket call payload
#         self.assertEqual(call_args["repo_url"], "https://bitbucket.org/test-owner/test-repo")
#         self.assertEqual(call_args["type"], "bitbucket")
#         self.assertTrue("messages" in call_args)
#         self.assertTrue(len(call_args["messages"]) > 0)
#         self.assertEqual(call_args["messages"][0]["role"], "user")

#     @patch('websockets.connect')
#     async def test_websocket_connection_success(self, mock_ws_connect):
#         """
#         Test successful WebSocket connection and data exchange.
#         """
#         # Create a mock for the WebSocket connection
#         mock_ws = AsyncMock()
#         mock_ws_connect.return_value.__aenter__.return_value = mock_ws
#         # Set up the mock to return a specific response when recv() is called
#         mock_ws.recv.side_effect = [
#             "Chunk 1 of response",
#             "Chunk 2 of response",
#             websockets.exceptions.ConnectionClosed(None, None)
#         ]
#         # Test data
#         request_data = {
#             "repo_url": "https://bitbucket.org/test-owner/test-repo",
#             "type": "bitbucket",
#             "messages": [{
#                 "role": "user",
#                 "content": "Test message content"
#             }]
#         }
#         # Call the WebSocket function
#         response = await call_websocket_chat(request_body=request_data)
#         # Verify WebSocket connection was established
#         mock_ws_connect.assert_called_once()
#         # Verify message was sent with correct data
#         mock_ws.send.assert_called_once_with(json.dumps(request_data))
#         # Verify response was received correctly
#         self.assertEqual(response, "Chunk 1 of responseChunk 2 of response")

#     @patch('websockets.connect')
#     async def test_websocket_connection_error(self, mock_ws_connect):
#         """
#         Test error handling during WebSocket connection.
#         """
#         # Simulate connection error
#         mock_ws_connect.side_effect = Exception("Connection failed")
#         # Test data
#         request_data = {
#             "repo_url": "https://bitbucket.org/test-owner/test-repo",
#             "type": "bitbucket",
#             "messages": [{
#                 "role": "user",
#                 "content": "Test message"
#             }]
#         }
#         # Call the WebSocket function
#         response = await call_websocket_chat(request_body=request_data)
#         # Verify error handling
#         self.assertTrue(response.startswith("Error:"))
#         self.assertIn("Connection failed", response)

#     @patch('api.bitbucket_api.call_websocket_chat')
#     async def test_invalid_repository_format(self, mock_websocket):
#         """
#         Test handling of invalid repository format.
#         """
#         # Create repository with invalid format
#         invalid_repo = Bi(
#             name="test-repo",
#             full_name="invalid-format", # Missing the owner/repo format
#             owner={"username": "test-owner"},
#             scm="git",
#             is_private=False
#         )
#         # Call function with invalid repo
#         result = await process_bitbucket_repository_async(invalid_repo)
#         # Verify that WebSocket was not called
#         mock_websocket.assert_not_called()

# def run_async_test(test_case):
#     """
#     Helper function to run async test cases.
#     Parameters:
#         test_case (function): Async test function to run
#     """
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(test_case)

if __name__ == '__main__':
    unittest.main()

