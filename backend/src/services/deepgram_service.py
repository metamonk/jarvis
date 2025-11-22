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
        #
        # Ensure sample_rate is properly set for initialization
        if 'sample_rate' not in params:
            params['sample_rate'] = 16000

        # Extract sample_rate from params to avoid duplicate keyword argument
        sample_rate = params.pop('sample_rate', 16000)

        # Import SSL cert configuration for Deepgram
        import os
        import certifi
        import ssl
        from deepgram import DeepgramClientOptions

        # Ensure SSL certificates are properly configured
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

        # For macOS SSL issues, we may need to disable SSL verification temporarily
        # This is a workaround for local development only
        # In production, proper SSL certificates should be configured
        import warnings
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        # Configure Deepgram client with custom options to handle SSL
        # Note: The Pipecat DeepgramSTT service handles its own client creation
        # but we ensure environment is properly configured before initialization

        # Enable verbose logging for Deepgram
        import logging
        logging.basicConfig(level=logging.DEBUG)
        deepgram_logger = logging.getLogger("deepgram")
        deepgram_logger.setLevel(logging.DEBUG)

        self._service = PipecatDeepgramSTT(
            api_key=self.api_key,
            audio_passthrough=False,
            sample_rate=sample_rate,
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
            logger.info("Starting audio processing in Deepgram service")
            async for frame in audio_frames:
                logger.debug(f"Processing audio frame: {len(frame.audio) if hasattr(frame, 'audio') else 0} bytes")
                # Process through Deepgram service with direction
                result_frames = await self._service.process_frame(
                    frame,
                    FrameDirection.DOWNSTREAM
                )

                # Yield transcription frames
                for result_frame in result_frames:
                    logger.debug(f"Got result frame: {type(result_frame).__name__}")
                    if isinstance(result_frame, TranscriptionFrame):
                        logger.info(
                            f"✅ Transcription received: {result_frame.text}"
                        )
                        yield result_frame

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    @property
    def is_ready(self) -> bool:
        """Check if service is ready to process audio."""
        return self._service is not None
