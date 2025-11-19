#!/usr/bin/env python3
"""
End-to-end testing for Jarvis Pipecat pipeline.

Tests the complete STT → LLM → TTS pipeline with mock data.
"""
import asyncio
import os
import sys
from pathlib import Path
from loguru import logger
from typing import AsyncIterator
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import DeepgramSTTService, OpenAILLMService, ElevenLabsTTSService
from src.config.settings import settings
from pipecat.frames.frames import TextFrame, AudioRawFrame


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


class PipelineTestSuite:
    """Test suite for Jarvis pipeline components."""

    def __init__(self):
        """Initialize test suite."""
        self.stt_service = None
        self.llm_service = None
        self.tts_service = None

    def verify_api_keys(self) -> bool:
        """Verify all required API keys are present."""
        logger.info("Verifying API keys...")

        required_keys = {
            "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
            "OPENAI_API_KEY": settings.OPENAI_API_KEY,
            "ELEVENLABS_API_KEY": settings.ELEVENLABS_API_KEY,
        }

        missing_keys = []
        for key_name, key_value in required_keys.items():
            if not key_value or key_value.startswith("your_"):
                missing_keys.append(key_name)
                logger.error(f"Missing or invalid: {key_name}")
            else:
                logger.success(f"Found: {key_name}")

        if missing_keys:
            logger.error(
                f"Missing API keys: {', '.join(missing_keys)}. "
                "Please configure them in .env file."
            )
            return False

        logger.success("All API keys verified")
        return True

    async def test_deepgram_stt(self) -> bool:
        """Test Deepgram STT service initialization."""
        logger.info("Testing Deepgram STT service...")

        try:
            self.stt_service = DeepgramSTTService(
                api_key=settings.DEEPGRAM_API_KEY
            )

            stt = self.stt_service.create_service(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=True
            )

            assert self.stt_service.is_ready, "STT service not ready"
            logger.success("Deepgram STT service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Deepgram STT test failed: {e}")
            return False

    async def test_openai_llm(self) -> bool:
        """Test OpenAI LLM service."""
        logger.info("Testing OpenAI LLM service...")

        try:
            self.llm_service = OpenAILLMService(
                api_key=settings.OPENAI_API_KEY
            )

            llm = self.llm_service.create_service(
                model="gpt-4-turbo-preview",
                temperature=0.7,
                max_tokens=150  # Limit for testing
            )

            self.llm_service.set_system_prompt(
                "You are a helpful assistant. Give very brief responses."
            )

            assert self.llm_service.is_ready, "LLM service not ready"
            logger.success("OpenAI LLM service initialized successfully")

            # Test a simple generation
            logger.info("Testing LLM response generation...")
            start_time = time.time()

            response = await self.llm_service.generate_response(
                "Say 'Hello, I am Jarvis' in a friendly way."
            )

            latency = time.time() - start_time

            logger.success(f"LLM Response (latency: {latency:.2f}s): {response}")

            assert len(response) > 0, "Empty response from LLM"
            assert latency < 10.0, f"LLM latency too high: {latency:.2f}s"

            return True

        except Exception as e:
            logger.error(f"OpenAI LLM test failed: {e}")
            return False

    async def test_elevenlabs_tts(self) -> bool:
        """Test ElevenLabs TTS service."""
        logger.info("Testing ElevenLabs TTS service...")

        try:
            self.tts_service = ElevenLabsTTSService(
                api_key=settings.ELEVENLABS_API_KEY
            )

            tts = self.tts_service.create_service(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
                model="eleven_turbo_v2_5",
                stability=0.5,
                similarity_boost=0.75,
                optimize_streaming_latency=3
            )

            assert self.tts_service.is_ready, "TTS service not ready"
            logger.success("ElevenLabs TTS service initialized successfully")

            # Test synthesis (without actually playing audio)
            logger.info("Testing TTS synthesis...")
            start_time = time.time()

            audio_frames = []
            async for frame in self.tts_service.synthesize_text("Hello, I am Jarvis."):
                audio_frames.append(frame)

            latency = time.time() - start_time

            logger.success(
                f"TTS Synthesis complete (latency: {latency:.2f}s): "
                f"{len(audio_frames)} audio frames generated"
            )

            assert len(audio_frames) > 0, "No audio frames generated"
            assert latency < 5.0, f"TTS latency too high: {latency:.2f}s"

            return True

        except Exception as e:
            logger.error(f"ElevenLabs TTS test failed: {e}")
            return False

    async def test_end_to_end_text_flow(self) -> bool:
        """Test end-to-end text flow through LLM and TTS."""
        logger.info("Testing end-to-end text flow (LLM → TTS)...")

        try:
            # Ensure services are initialized
            if not self.llm_service or not self.tts_service:
                logger.error("Services not initialized")
                return False

            # Test question
            user_input = "What is the capital of France?"

            logger.info(f"User input: {user_input}")

            # Step 1: LLM processing
            start_time = time.time()
            llm_response = await self.llm_service.generate_response(user_input)
            llm_latency = time.time() - start_time

            logger.info(f"LLM response (latency: {llm_latency:.2f}s): {llm_response}")

            # Step 2: TTS synthesis
            start_time = time.time()
            audio_frames = []
            async for frame in self.tts_service.synthesize_text(llm_response):
                audio_frames.append(frame)
            tts_latency = time.time() - start_time

            total_latency = llm_latency + tts_latency

            logger.success(
                f"End-to-end flow complete:\n"
                f"  - LLM latency: {llm_latency:.2f}s\n"
                f"  - TTS latency: {tts_latency:.2f}s\n"
                f"  - Total latency: {total_latency:.2f}s\n"
                f"  - Audio frames: {len(audio_frames)}"
            )

            # Latency assertions
            assert llm_latency < 10.0, f"LLM latency too high: {llm_latency:.2f}s"
            assert tts_latency < 5.0, f"TTS latency too high: {tts_latency:.2f}s"
            assert total_latency < 15.0, f"Total latency too high: {total_latency:.2f}s"

            return True

        except Exception as e:
            logger.error(f"End-to-end test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("=" * 80)
        logger.info("Starting Jarvis Pipeline Test Suite")
        logger.info("=" * 80)

        results = {
            "API Keys": self.verify_api_keys(),
        }

        if not results["API Keys"]:
            logger.error("API key verification failed. Cannot proceed with tests.")
            return False

        # Run async tests
        results["Deepgram STT"] = await self.test_deepgram_stt()
        results["OpenAI LLM"] = await self.test_openai_llm()
        results["ElevenLabs TTS"] = await self.test_elevenlabs_tts()
        results["End-to-End Flow"] = await self.test_end_to_end_text_flow()

        # Print summary
        logger.info("=" * 80)
        logger.info("Test Summary")
        logger.info("=" * 80)

        all_passed = True
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            color = "green" if passed else "red"
            logger.info(f"  {test_name}: <{color}>{status}</{color}>")
            if not passed:
                all_passed = False

        logger.info("=" * 80)

        if all_passed:
            logger.success("All tests passed!")
        else:
            logger.error("Some tests failed.")

        return all_passed


async def main():
    """Main test entry point."""
    test_suite = PipelineTestSuite()
    success = await test_suite.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
