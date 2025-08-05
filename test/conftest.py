"""
Pytest configuration and shared fixtures for webhook_autodoc tests.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path so imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ.setdefault("Github_WEBHOOK_SECRET", "test_secret_default")
