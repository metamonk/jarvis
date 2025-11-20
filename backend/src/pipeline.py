"""Pipecat voice pipeline orchestrator for Jarvis."""
from typing import Optional, List, Dict, Any

import httpx
from loguru import logger
from pipecat.frames.frames import EndFrame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from .config.settings import settings
from .services import DeepgramSTTService, OpenAILLMService


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

        # Configuration
        self.voice_id = voice_id
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Pipeline components
        self._pipeline: Optional[Pipeline] = None
        self._task: Optional[PipelineTask] = None
        self._runner: Optional[PipelineRunner] = None

        # Buffer for accumulating the current assistant response text so we can
        # synthesize it via ElevenLabs once the LLM response is complete.
        self._current_tts_text: str = ""

        logger.info("Jarvis Pipeline initialized")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for Jarvis."""
        return (
            "You are Jarvis, a helpful AI assistant. "
            "You provide concise, accurate responses to user queries. "
            "You can search documents, access GitHub code, and use company APIs. "
            "Always be professional and helpful."
        )

    async def setup(self, transport):
        """
        Set up the pipeline with all components.

        Args:
            transport: Transport layer for audio I/O
        """
        from src.transport import WebSocketTransport  # avoid circular import in tools/tests

        logger.info("Setting up Jarvis pipeline...")

        if not isinstance(transport, WebSocketTransport):
            raise TypeError(
                "JarvisPipeline.setup expects a WebSocketTransport instance for audio I/O."
            )

        # Create service instances
        stt = self.stt_service.create_service(
            model="nova-2",
            language="en-US",
            smart_format=True,
            interim_results=True,
        )
        # Create the underlying OpenAI service used by our wrapper. We won't add
        # this processor to the Pipecat pipeline; instead we call the wrapper's
        # high-level `generate_response` helper when we receive finalized STT
        # transcriptions.
        self.llm_service.create_service(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=1024,
        )

        # Set system prompt
        self.llm_service.set_system_prompt(self.system_prompt)

        # Observe STT output frames so we can trigger LLM + TTS when a
        # transcription is ready.
        @stt.event_handler("on_after_process_frame")
        async def _stt_after(stt_proc, frame):
            frame_type = type(frame).__name__

            if isinstance(frame, TranscriptionFrame):
                text = (getattr(frame, "text", "") or "").strip()
                is_final = getattr(frame, "is_final", True)

                if not text:
                    logger.debug(
                        f"Deepgram STT produced TranscriptionFrame with empty text "
                        f"(final={is_final})"
                    )
                    return

                logger.info(
                    f"Deepgram STT transcription (final={is_final}): [{text}]"
                )

                # For now we only respond to final transcriptions to avoid
                # generating multiple replies for interim results. If the field
                # doesn't exist, we treat the frame as final.
                if not is_final:
                    return

                try:
                    logger.info("Generating LLM response for transcribed speech")
                    response_text = await self.llm_service.generate_response(text)
                    logger.info(f"LLM response for speech: [{response_text}]")
                    await self._speak_with_elevenlabs(response_text, transport)
                except Exception as e:
                    logger.error(f"Error handling STT transcription frame: {e}")
            else:
                logger.debug(f"STT downstream non-transcription frame: {frame_type}")

        # Build core pipeline: Audio → STT
        # LLM + TTS are handled out-of-band in the STT event handler above.
        self._pipeline = Pipeline(
            [
                stt,  # Speech-to-Text
            ]
        )

        # Create task
        self._task = PipelineTask(self._pipeline)

        # Attach the WebSocket transport to the task so it can inject audio frames.
        await transport.setup(self._task)

        @self._task.event_handler("on_frame_reached_downstream")
        async def _on_downstream(task, frame):
            frame_type = type(frame).__name__

            if isinstance(frame, TranscriptionFrame):
                text = (getattr(frame, "text", "") or "").strip()
                is_final = getattr(frame, "is_final", True)

                if not text:
                    logger.debug(
                        f"Received TranscriptionFrame with empty text (final={is_final})"
                    )
                    return

                logger.info(
                    f"Received transcription from STT (final={is_final}): [{text}]"
                )

                # Only trigger LLM + TTS on final transcriptions to avoid
                # responding to interim results.
                if not is_final:
                    return

                try:
                    logger.info("Generating LLM response for transcribed speech")
                    response_text = await self.llm_service.generate_response(text)
                    logger.info(f"LLM response for speech: [{response_text}]")
                    await self._speak_with_elevenlabs(response_text, transport)
                except Exception as e:
                    logger.error(f"Error handling transcription frame: {e}")
            else:
                logger.debug(f"Pipeline downstream non-transcription frame: {frame_type}")

        logger.info("Pipeline setup complete")

    async def _speak_with_elevenlabs(self, text: str, transport) -> None:
        """
        Use ElevenLabs HTTP API to synthesize speech for the given text and
        stream raw PCM audio bytes back to the browser via the WebSocket
        transport.

        This bypasses Pipecat's built‑in ElevenLabs processor and gives us full
        control over the audio format so it matches what the frontend expects
        (16‑bit PCM at 16kHz, mono).
        """
        api_key = settings.ELEVENLABS_API_KEY
        if not api_key:
            logger.error("ELEVENLABS_API_KEY is not configured; cannot synthesize speech")
            return

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"

        headers = {
            "xi-api-key": api_key,
            "Accept": "application/octet-stream",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            # Request 16kHz 16‑bit PCM, which the frontend decodes directly.
            "output_format": "pcm_16000",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        logger.info("Calling ElevenLabs TTS HTTP API for synthesis")

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()

                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue

                    logger.info(
                        "Streaming ElevenLabs audio chunk to WebSocket: "
                        f"{len(chunk)} bytes"
                    )
                    await transport.websocket.send_bytes(chunk)

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
            self._pipeline is not None
        )
