"""Pipecat voice pipeline orchestrator for Jarvis."""
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import (
    Frame,
    AudioRawFrame,
    TextFrame,
    TranscriptionFrame,
    LLMMessagesFrame,
    EndFrame
)
from pipecat.transports.base_transport import BaseTransport

from .services import DeepgramSTTService, OpenAILLMService, ElevenLabsTTSService
from .config.settings import settings
from loguru import logger
from typing import Optional, List, Dict, Any
import asyncio


class JarvisPipeline:
    """
    Main voice pipeline orchestrator.

    Implements the complete STT → LLM → TTS pipeline using Pipecat.
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    ):
        """
        Initialize Jarvis pipeline.

        Args:
            system_prompt: System prompt for the LLM
            voice_id: ElevenLabs voice ID
        """
        # Initialize services
        self.stt_service = DeepgramSTTService(
            api_key=settings.DEEPGRAM_API_KEY
        )
        self.llm_service = OpenAILLMService(
            api_key=settings.OPENAI_API_KEY
        )
        self.tts_service = ElevenLabsTTSService(
            api_key=settings.ELEVENLABS_API_KEY
        )

        # Configuration
        self.voice_id = voice_id
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Pipeline components
        self._pipeline: Optional[Pipeline] = None
        self._task: Optional[PipelineTask] = None
        self._runner: Optional[PipelineRunner] = None

        logger.info("Jarvis Pipeline initialized")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for Jarvis."""
        return (
            "You are Jarvis, a helpful AI assistant. "
            "You provide concise, accurate responses to user queries. "
            "You can search documents, access GitHub code, and use company APIs. "
            "Always be professional and helpful."
        )

    async def setup(self, transport: BaseTransport):
        """
        Set up the pipeline with all components.

        Args:
            transport: Transport layer for audio I/O
        """
        logger.info("Setting up Jarvis pipeline...")

        # Create service instances
        stt = self.stt_service.create_service(
            model="nova-2",
            language="en-US",
            smart_format=True,
            interim_results=True
        )

        llm = self.llm_service.create_service(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=1024
        )

        tts = self.tts_service.create_service(
            voice_id=self.voice_id,
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.75,
            optimize_streaming_latency=3
        )

        # Set system prompt
        self.llm_service.set_system_prompt(self.system_prompt)

        # Create aggregators
        user_aggregator = LLMUserResponseAggregator()
        assistant_aggregator = LLMAssistantResponseAggregator()

        # Build pipeline
        # Audio → STT → User Aggregator → LLM → Assistant Aggregator → TTS → Audio
        self._pipeline = Pipeline([
            transport.input(),     # Audio input
            stt,                   # Speech-to-Text
            user_aggregator,       # Aggregate user transcription
            llm,                   # Language Model
            assistant_aggregator,  # Aggregate LLM response
            tts,                   # Text-to-Speech
            transport.output(),    # Audio output
        ])

        # Create task
        self._task = PipelineTask(self._pipeline)

        logger.info("Pipeline setup complete")

    async def run(self):
        """Run the pipeline."""
        if not self._task:
            raise RuntimeError("Pipeline not set up. Call setup() first.")

        logger.info("Starting pipeline...")

        try:
            # Create runner
            self._runner = PipelineRunner()

            # Run the pipeline task
            await self._runner.run(self._task)

            logger.info("Pipeline completed")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise

    async def stop(self):
        """Stop the pipeline gracefully."""
        if self._task:
            logger.info("Stopping pipeline...")
            await self._task.queue_frame(EndFrame())
            logger.info("Pipeline stopped")

    def set_system_prompt(self, prompt: str):
        """
        Update the system prompt.

        Args:
            prompt: New system prompt
        """
        self.system_prompt = prompt
        self.llm_service.set_system_prompt(prompt)
        logger.info(f"System prompt updated: {prompt[:100]}...")

    def clear_conversation(self):
        """Clear conversation history."""
        self.llm_service.clear_history(keep_system_prompt=True)
        logger.info("Conversation cleared")

    @property
    def conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.llm_service.history

    @property
    def is_ready(self) -> bool:
        """Check if pipeline is ready."""
        return (
            self.stt_service.is_ready and
            self.llm_service.is_ready and
            self.tts_service.is_ready and
            self._pipeline is not None
        )
