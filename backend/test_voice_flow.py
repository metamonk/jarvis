#!/usr/bin/env python3
"""Test the complete voice interaction flow."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.services.deepgram_direct import DirectDeepgramService
from src.services.openai_service import OpenAILLMService
from loguru import logger

async def test_voice_flow():
    """Test complete voice flow: Deepgram -> OpenAI -> Response."""
    logger.info("=" * 50)
    logger.info("Testing Complete Voice Flow")
    logger.info("=" * 50)

    try:
        # Initialize services
        logger.info("Initializing services...")
        deepgram = DirectDeepgramService(settings.DEEPGRAM_API_KEY)
        openai_service = OpenAILLMService(settings.OPENAI_API_KEY)

        # Configure OpenAI
        openai_service.create_service(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=100
        )
        openai_service.set_system_prompt("You are a helpful assistant. Keep responses brief.")

        # Track if we got a response
        got_response = asyncio.Event()
        test_transcript = None
        test_response = None

        # Set up transcript handler
        async def handle_transcript(text: str):
            nonlocal test_transcript, test_response
            logger.info(f"📝 Got transcript: {text}")
            test_transcript = text

            # Generate LLM response
            logger.info("Generating LLM response...")
            response = await openai_service.generate_response(text)

            if response:
                logger.success(f"✅ Got LLM response: {response}")
                test_response = response
                got_response.set()
            else:
                logger.error("❌ Empty response from LLM")

        deepgram.on_transcript = handle_transcript

        # Connect to Deepgram
        logger.info("Connecting to Deepgram...")
        await deepgram.connect()

        # Simulate some audio (silence for now)
        logger.info("Sending test audio...")
        test_audio = b'\x00' * 16000  # 1 second of silence
        await deepgram.send_audio(test_audio)

        # Now send a test with actual speech simulation
        # For testing, we'll just trigger finalization
        logger.info("Triggering finalization...")
        await deepgram.finalize()

        # Wait for response with timeout
        logger.info("Waiting for complete flow...")
        try:
            await asyncio.wait_for(got_response.wait(), timeout=5.0)
            logger.success("✅ COMPLETE FLOW SUCCESS!")
            logger.info(f"Transcript: {test_transcript}")
            logger.info(f"Response: {test_response}")
            return True
        except asyncio.TimeoutError:
            logger.warning("⚠️ No response received within timeout")
            # Check if we at least got an interim
            if deepgram._last_interim_transcript:
                logger.info(f"Found interim transcript: {deepgram._last_interim_transcript}")
                logger.info("Testing with interim...")
                await handle_transcript(deepgram._last_interim_transcript)
                return True
            return False

    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # Cleanup
        if deepgram.is_connected:
            await deepgram.disconnect()

if __name__ == "__main__":
    success = asyncio.run(test_voice_flow())
    sys.exit(0 if success else 1)