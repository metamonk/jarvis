"""Deepgram Speech-to-Text service using Pipecat."""
from pipecat.services.deepgram.stt import DeepgramSTTService as PipecatDeepgramSTT
from pipecat.frames.frames import Frame, AudioRawFrame, TranscriptionFrame
from loguru import logger
from typing import AsyncIterator


class DeepgramSTTService:
    """
    Wrapper for Pipecat's Deepgram STT service.

    Provides speech-to-text capabilities using Deepgram's Nova-2 model.
    """

    def __init__(self, api_key: str):
        """
        Initialize Deepgram STT service.

        Args:
            api_key: Deepgram API key
        """
        self.api_key = api_key
        self._service = None
        logger.info("Deepgram STT Service initialized")

    def create_service(
        self,
        language: str = "en-US",
        model: str = "nova-2",
        smart_format: bool = True,
        interim_results: bool = True,
        **kwargs
    ) -> PipecatDeepgramSTT:
        """
        Create a Pipecat Deepgram STT service instance.

        Args:
            language: Language code (default: en-US)
            model: Deepgram model to use (default: nova-2)
            smart_format: Enable smart formatting
            interim_results: Enable interim transcription results
            **kwargs: Additional Deepgram parameters

        Returns:
            PipecatDeepgramSTT: Configured Deepgram service
        """
        params = {
            "language": language,
            "model": model,
            "smart_format": smart_format,
            "interim_results": interim_results,
            **kwargs
        }

        logger.info(f"Creating Deepgram STT service with params: {params}")

        # Disable audio passthrough so that only synthesized TTS audio is sent
        # back to the client. Without this, the raw microphone audio is pushed
        # downstream and echoed back to the WebSocket, which is why the user
        # was hearing themselves instead of just Jarvis.
        self._service = PipecatDeepgramSTT(
            api_key=self.api_key,
            audio_passthrough=False,
            **params,
        )

        return self._service

    async def process_audio(
        self,
        audio_frames: AsyncIterator[AudioRawFrame]
    ) -> AsyncIterator[TranscriptionFrame]:
        """
        Process audio frames and yield transcription frames.

        Args:
            audio_frames: Async iterator of audio frames

        Yields:
            TranscriptionFrame: Transcribed text frames
        """
        if not self._service:
            raise RuntimeError(
                "Service not created. Call create_service() first."
            )

        try:
            from pipecat.processors.frame_processor import FrameDirection
            async for frame in audio_frames:
                # Process through Deepgram service with direction
                result_frames = await self._service.process_frame(
                    frame,
                    FrameDirection.DOWNSTREAM
                )

                # Yield transcription frames
                for result_frame in result_frames:
                    if isinstance(result_frame, TranscriptionFrame):
                        logger.debug(
                            f"Transcription: {result_frame.text}"
                        )
                        yield result_frame

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    @property
    def is_ready(self) -> bool:
        """Check if service is ready to process audio."""
        return self._service is not None
