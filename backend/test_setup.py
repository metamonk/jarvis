#!/usr/bin/env python3
"""
Test script to verify backend environment is correctly configured.
"""

import sys
import importlib


def test_python_version():
    """Verify Python version is 3.11 or higher."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version {version.major}.{version.minor} is too old (need 3.11+)")
        return False


def test_import(module_name, package_name=None):
    """Test if a module can be imported."""
    display_name = package_name or module_name
    try:
        importlib.import_module(module_name)
        print(f"✓ {display_name} installed")
        return True
    except ImportError:
        print(f"✗ {display_name} not installed")
        return False


def main():
    """Run all setup tests."""
    print("=" * 50)
    print("Jarvis Backend Environment Test")
    print("=" * 50)
    print()

    tests = [
        ("Python Version", test_python_version()),
        ("FastAPI", test_import("fastapi")),
        ("Uvicorn", test_import("uvicorn")),
        ("Pipecat", test_import("pipecat", "pipecat-ai")),
        ("OpenAI", test_import("openai")),
        ("Pinecone", test_import("pinecone")),
        ("HTTPX", test_import("httpx")),
        ("Python-dotenv", test_import("dotenv", "python-dotenv")),
        ("Loguru", test_import("loguru")),
        ("Pydantic", test_import("pydantic")),
    ]

    print()
    print("=" * 50)
    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed! Environment is ready.")
        return 0
    else:
        print("✗ Some tests failed. Run: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
