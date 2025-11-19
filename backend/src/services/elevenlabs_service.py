"""ElevenLabs Text-to-Speech service using Pipecat."""
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService as PipecatElevenLabsTTS
from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, StartFrame
from loguru import logger
from typing import AsyncIterator, Optional
import ssl
import certifi

# Download required NLTK data for Pipecat's text processing
try:
    import nltk
    # Set SSL context for NLTK downloads
    ssl._create_default_https_context = ssl._create_unverified_context
    nltk.download('punkt_tab', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception as e:
    logger.warning(f"Could not download NLTK data: {e}. Text processing may be limited.")


class ElevenLabsTTSService:
    """
    Wrapper for Pipecat's ElevenLabs TTS service.

    Provides text-to-speech capabilities using ElevenLabs Turbo v2.5.
    """

    def __init__(self, api_key: str):
        """
        Initialize ElevenLabs TTS service.

        Args:
            api_key: ElevenLabs API key
        """
        self.api_key = api_key
        self._service = None
        logger.info("ElevenLabs TTS Service initialized")

    def create_service(
        self,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default: Rachel
        model: str = "eleven_turbo_v2_5",
        language: str = "en",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        optimize_streaming_latency: int = 3,
        **kwargs
    ) -> PipecatElevenLabsTTS:
        """
        Create a Pipecat ElevenLabs TTS service instance.

        Args:
            voice_id: ElevenLabs voice ID (default: Rachel)
            model: ElevenLabs model (default: eleven_turbo_v2_5)
            language: Language code (default: en)
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice similarity (0.0-1.0)
            style: Voice style exaggeration (0.0-1.0)
            use_speaker_boost: Enable speaker boost
            optimize_streaming_latency: Latency optimization (0-4)
            **kwargs: Additional ElevenLabs parameters

        Returns:
            PipecatElevenLabsTTS: Configured ElevenLabs service
        """
        voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }

        params = {
            "voice_id": voice_id,
            "model": model,
            "language": language,
            "voice_settings": voice_settings,
            "optimize_streaming_latency": optimize_streaming_latency,
            **kwargs
        }

        logger.info(f"Creating ElevenLabs TTS service with params: {params}")

        self._service = PipecatElevenLabsTTS(
            api_key=self.api_key,
            **params
        )

        return self._service

    async def process_text(
        self,
        text_frames: AsyncIterator[TextFrame]
    ) -> AsyncIterator[AudioRawFrame]:
        """
        Process text frames and yield audio frames.

        Args:
            text_frames: Async iterator of text frames

        Yields:
            AudioRawFrame: Synthesized audio frames
        """
        if not self._service:
            raise RuntimeError(
                "Service not created. Call create_service() first."
            )

        try:
            from pipecat.processors.frame_processor import FrameDirection
            async for frame in text_frames:
                # Process through ElevenLabs service with direction
                result_frames = await self._service.process_frame(
                    frame,
                    FrameDirection.DOWNSTREAM
                )

                # Yield audio frames
                for result_frame in result_frames:
                    if isinstance(result_frame, AudioRawFrame):
                        logger.debug(
                            f"Audio frame generated: {len(result_frame.audio)} bytes"
                        )
                        yield result_frame

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            raise

    async def synthesize_text(self, text: str) -> AsyncIterator[AudioRawFrame]:
        """
        Synthesize a single text string to audio.

        Args:
            text: Text to synthesize

        Yields:
            AudioRawFrame: Synthesized audio frames
        """
        if not self._service:
            raise RuntimeError(
                "Service not created. Call create_service() first."
            )

        try:
            from pipecat.processors.frame_processor import FrameDirection

            # NOTE: This method is designed to work within a Pipecat pipeline context.
            # In production, this will be called within a PipelineTask with proper
            # TaskManager initialization.

            # Create text frame
            text_frame = TextFrame(text=text)

            # Process through ElevenLabs service
            result_frames = await self._service.process_frame(
                text_frame,
                FrameDirection.DOWNSTREAM
            )

            # Yield audio frames
            if result_frames:
                for result_frame in result_frames:
                    if isinstance(result_frame, AudioRawFrame):
                        logger.debug(
                            f"Audio frame generated: {len(result_frame.audio)} bytes"
                        )
                        yield result_frame

        except Exception as e:
            logger.error(f"Error synthesizing text: {e}")
            raise

    @property
    def is_ready(self) -> bool:
        """Check if service is ready to process text."""
        return self._service is not None

    @staticmethod
    def get_available_voices() -> dict:
        """
        Get commonly used ElevenLabs voice IDs.

        Returns:
            dict: Voice name to ID mapping
        """
        return {
            "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, confident
            "domi": "AZnzlk1XvdvUeBnXmlld",    # Female, strong
            "bella": "EXAVITQu4vr4xnSDxMaL",   # Female, soft
            "antoni": "ErXwobaYiN019PkySvjV",  # Male, well-rounded
            "elli": "MF3mGyEYCl7XYWbV9V6O",    # Male, energetic
            "josh": "TxGEqnHWrfWFTfGW9XjX",    # Male, deep
            "arnold": "VR6AewLTigWG4xSOukaG",  # Male, crisp
            "adam": "pNInz6obpgDQGcFmaJgB",    # Male, deep
            "sam": "yoZ06aMxZJJ28mfd3POQ",     # Male, dynamic
        }
