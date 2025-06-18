import os
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # Get port from environment variable or use default
    webhook_port = int(os.environ.get("WEBHOOK_PORT", 8002))

    logger.info(f"Starting Uvicorn server for FastAPI app on port {webhook_port}")

    # Run the webhook FastAPI app (located in main.py) with uvicorn
    # The string "api.web_hook.main:app" tells uvicorn where to find the FastAPI app instance.
    # - "api.web_hook.main" is the module path.
    # - "app" is the variable name assigned to FastAPI() in main.py.
    uvicorn.run(
        "api.web_hook.main:app", # Points to the 'app' instance in 'api/web_hook/main.py'
        host="0.0.0.0",
        port=webhook_port,
        reload=True, # Reloads the server when code changes, useful for development
    )
