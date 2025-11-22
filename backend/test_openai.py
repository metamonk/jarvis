#!/usr/bin/env python3
"""Test script to verify OpenAI API is working."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.services.openai_service import OpenAILLMService
from loguru import logger

async def test_openai():
    """Test OpenAI API directly."""
    logger.info("=" * 50)
    logger.info("Testing OpenAI API")
    logger.info("=" * 50)

    try:
        # Initialize the service
        logger.info(f"API Key prefix: {settings.OPENAI_API_KEY[:20]}...")
        service = OpenAILLMService(settings.OPENAI_API_KEY)

        # Create the service
        service.create_service(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=100
        )
        service.set_system_prompt("You are a helpful assistant. Keep responses brief.")

        # Test the direct API call
        logger.info("Testing generate_response method...")
        response = await service.generate_response("Say hello and tell me you're working.")

        if response:
            logger.success(f"✅ SUCCESS! Response: {response}")
            return True
        else:
            logger.error("❌ FAILED: Empty response")
            return False

    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai())
    sys.exit(0 if success else 1)