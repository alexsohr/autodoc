import os
# import logging # Removed
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger # Removed
# It's good practice to configure logging at the application entry point # Removed
# or in a dedicated logging configuration module. # Removed
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Removed
# logger = logging.getLogger(__name__) # Removed

# The FastAPI app instance is now created in main.py
# from api.web_hook.main import app # No longer needed here if only running uvicorn

if __name__ == "__main__":
    # Get port from environment variable or use default
    webhook_port = int(os.environ.get("WEBHOOK_PORT", 8002))

    # logger.info(f"Starting Uvicorn server for FastAPI app on port {webhook_port}") # Removed
    print(f"Attempting to start Uvicorn server for FastAPI app on port {webhook_port}") # Optional: replaced with print

    # Run the webhook FastAPI app (located in main.py) with uvicorn
    # The string "api.web_hook.main:app" tells uvicorn where to find the FastAPI app instance.
    # - "api.web_hook.main" is the module path.
    # - "app" is the variable name assigned to FastAPI() in main.py.
    uvicorn.run(
        "api.web_hook.main:app", # Points to the 'app' instance in 'api/web_hook/main.py'
        host="0.0.0.0",
        port=webhook_port,
        reload=True, # Reloads the server when code changes, useful for development
        # workers=int(os.environ.get("WEB_CONCURRENCY", 1)) # Example for setting workers
    )
