import os
import json
import hmac
import hashlib
import logging
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.web_hook.github_models import GithubPushEvent
from api.web_hook.wiki_generation_service import generate_wiki_for_repository

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure basic config for logger if not configured elsewhere

app = FastAPI(
    title="Github Webhook API",
    description="API for webhooks"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for GitHub issue events. This will be the dedicated entry point for GitHub issue events.
    It immediately returns a 202 Accepted response and starts the generation process in the background.
    Args:
        request: The incoming request containing the GitHub webhook payload
        background_tasks: FastAPI's BackgroundTasks for async processing
    Returns:
        A 202 Accepted response indicating the webhook was received and processing has started
    """
    try:
        # Parse the webhook payload
        payload = await request.json()
        body = await request.body()
        # Extract GitHub event type from headers
        github_event_type = request.headers.get("X-GitHub-Event")
        logger.info(f"Received GitHub webhook event: {github_event_type}")
        logger.debug(f"Request headers: {request.headers}")


        # Validate HMAC-SHA256 signature
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature:
            logger.error("Missing HMAC-SHA256 signature in webhook headers")
            raise HTTPException(status_code=400, detail="Missing HMAC-SHA256 signature")

        secret = os.environ.get("Github_WEBHOOK_SECRET", "")
        if not secret:
            logger.error("Webhook secret not configured in environment variables")
            # It's better to return a generic error to the client for security reasons
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        hash_object = hmac.new(secret.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            logger.error(f"Request signatures didn't match!")
            raise HTTPException(status_code=403, detail="Request signatures didn't match!")

        # Assuming GithubPushEvent is the correct model for 'pull_request' events as well based on previous context
        # If not, this might need adjustment or a more generic event parsing.
        github_push_event = GithubPushEvent(**payload)

        if github_event_type == "pull_request" and \
           github_push_event.action == "closed" and \
           github_push_event.pull_request.merged and \
           github_push_event.pull_request.base.ref == github_push_event.repository.default_branch:

            logger.info(f"Processing GitHub event: {github_push_event.action} for pull request #{github_push_event.number} in repo {github_push_event.repository.full_name}")

            # Add the background task for processing
            background_tasks.add_task(
                generate_wiki_for_repository,
                github_event=github_push_event
                # actor_name can be passed if needed by generate_wiki_for_repository
            )
            logger.info(f"Background task added for processing repository: {github_push_event.repository.full_name}")
            return JSONResponse(
                status_code=202,
                content={"message": f"Webhook received. Processing repository {github_push_event.repository.full_name} in background."}
            )
        else:
            logger.info(f"Received event type '{github_event_type}' with action '{github_push_event.action}'. No processing configured for this event.")
            return JSONResponse(
                status_code=202, # Acknowledge other events but don't process
                content={"message": "Webhook received, but event type or action is not configured for processing."}
            )
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON in webhook payload")
    except HTTPException as he:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise he
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        # Return a generic 500 error for unhandled exceptions
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Note: The uvicorn run command will remain in github_api.py for now,
# but will be updated to run this app: "api.web_hook.main:app"
