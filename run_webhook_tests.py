#!/usr/bin/env python3
"""
Test runner script for webhook_autodoc project.
Run this script to execute all tests for the github_webhook function.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run the test suite for github_webhook function."""
    
    # Ensure we're in the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Set up environment variables for testing
    os.environ["Github_WEBHOOK_SECRET"] = "test_secret"
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest", 
        "test/api/web_hook/test_app.py",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-x",  # Stop on first failure
    ]
    
    print("Running tests for github_webhook function...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 60)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("-" * 60)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("   pip install pytest pytest-asyncio")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
