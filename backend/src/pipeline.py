"""Pipecat voice pipeline orchestrator for Jarvis."""
from typing import Optional, List, Dict, Any

import httpx
from loguru import logger
from pipecat.frames.frames import EndFrame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from .config.settings import settings
from .services import DeepgramSTTService, OpenAILLMService
from .services.deepgram_direct import DirectDeepgramService


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

        # Direct Deepgram service as fallback
        self.direct_deepgram = DirectDeepgramService(
            api_key=settings.DEEPGRAM_API_KEY
        )
        self.use_direct_deepgram = True  # Force direct implementation

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

        # Audio buffer for direct Deepgram
        self._audio_buffer = bytearray()

        logger.info("Jarvis Pipeline initialized")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for Jarvis."""
        return (
            "You are Jarvis, a helpful AI voice assistant. "
            "You can hear and respond to users through voice conversations. "
            "You provide concise, accurate responses to user queries. "
            "Keep responses brief and conversational since you're speaking. "
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

        # Set up direct Deepgram connection
        if self.use_direct_deepgram:
            logger.info("Using direct Deepgram implementation")
            connected = await self.direct_deepgram.connect()
            if not connected:
                logger.error("Failed to establish direct Deepgram connection!")
                raise RuntimeError("Critical: Cannot connect to Deepgram!")

            # Initialize LLM service
            self.llm_service.create_service(
                model="gpt-4-turbo-preview",
                temperature=0.7,
                max_tokens=1024,
            )
            self.llm_service.set_system_prompt(self.system_prompt)

            # Set up transcript callback
            async def handle_transcript(text: str):
                logger.info(f"🎯 Got transcript: {text}")
                logger.info("📍 Entering try block for LLM response generation...")
                try:
                    logger.info("🚀 About to call generate_response...")
                    # Generate LLM response
                    response = await self.llm_service.generate_response(text)
                    logger.info(f"✅ LLM response received: {response[:100] if response else 'Empty response'}...")

                    if not response:
                        logger.warning("⚠️ Empty response from LLM, skipping TTS")
                        return

                    # Send TTS
                    logger.info("🔊 Sending response to TTS...")
                    await self._speak_with_elevenlabs(response, transport)
                    logger.info("✅ TTS complete")
                except Exception as e:
                    logger.error(f"❌ Error processing transcript: {e}")
                    logger.error(f"Error type: {type(e).__name__}")
                    import traceback
                    logger.error(f"Traceback:\n{traceback.format_exc()}")

            self.direct_deepgram.on_transcript = handle_transcript

            # Store reference to transport for audio handling
            self.transport = transport
            return  # Skip Pipecat pipeline setup

        # Create service instances with proper parameters
        # Note: We pass sample_rate to ensure proper initialization
        stt = self.stt_service.create_service(
            model="nova-2",
            language="en-US",
            smart_format=True,
            interim_results=True,
            sample_rate=16000,  # Explicitly set sample rate for proper initialization
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

        # Add event handlers for Deepgram connection status
        @stt.event_handler("on_connected")
        async def _on_stt_connected(processor):
            logger.info("✅ Deepgram STT successfully connected!")

        @stt.event_handler("on_disconnected")
        async def _on_stt_disconnected(processor):
            logger.warning("⚠️ Deepgram STT disconnected!")

        @stt.event_handler("on_connection_error")
        async def _on_stt_error(processor, error):
            logger.error(f"❌ Deepgram STT connection error: {error}")

        # Observe STT output frames so we can trigger LLM + TTS when a
        # transcription is ready.
        @stt.event_handler("on_after_process_frame")
        async def _stt_after(stt_proc, frame):
            frame_type = type(frame).__name__

            # Log all frame types for debugging
            if frame_type == "AudioRawFrame":
                audio_size = len(frame.audio) if hasattr(frame, 'audio') and frame.audio else 0
                logger.debug(f"STT processing AudioRawFrame: {audio_size} bytes")
            else:
                logger.debug(f"STT processing frame: {frame_type}")

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
                    f"🎯 Deepgram STT transcription (final={is_final}): [{text}]"
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

        # Build core pipeline: Audio → STT
        # LLM + TTS are handled out-of-band in the STT event handler above.
        # We need to ensure the STT service is properly connected to receive frames
        self._pipeline = Pipeline(
            [
                stt,  # Speech-to-Text processor
            ]
        )

        # Create task with proper pipeline configuration
        # The task will handle StartFrame propagation and frame routing
        self._task = PipelineTask(
            self._pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=False,
                enable_usage_metrics=False,
            ),
        )

        # We only care about transcription frames reaching the end of the
        # pipeline; configure the task so it will fire the corresponding event
        # handler only for those frame types.
        self._task.set_reached_downstream_filter((TranscriptionFrame,))

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

        # ElevenLabs requires output_format as a URL parameter, not in JSON payload
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream?output_format=pcm_16000"

        headers = {
            "xi-api-key": api_key,
            "Accept": "application/octet-stream",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            # output_format is now in the URL query parameter
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

                # Log response headers to verify format
                content_type = resp.headers.get('content-type', 'unknown')
                logger.info(f"ElevenLabs response content-type: {content_type}")

                # Buffer small chunks to avoid audio crackling
                buffer = bytearray()
                # Use 8192 bytes (4096 samples) for proper PCM frame alignment
                # 16-bit = 2 bytes per sample, so 8192 bytes = 4096 samples
                CHUNK_SIZE = 8192  # Aligned with 16-bit PCM frame boundaries

                first_chunk = True
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue

                    # Log first chunk to verify PCM format
                    if first_chunk and len(chunk) >= 16:
                        first_bytes = chunk[:16]
                        hex_preview = ' '.join(f'{b:02x}' for b in first_bytes)
                        logger.info(f"First audio bytes (hex): {hex_preview}")

                        # Check for common audio format signatures
                        if chunk[:4] == b'RIFF':
                            logger.error("❌ Audio is WAV format, not raw PCM!")
                        elif chunk[:3] == b'ID3' or chunk[:2] == b'\xff\xfb':
                            logger.error("❌ Audio is MP3 format, not raw PCM!")
                        else:
                            logger.info("✅ Audio appears to be raw PCM")
                        first_chunk = False

                    buffer.extend(chunk)

                    # Send buffered data when we have enough
                    while len(buffer) >= CHUNK_SIZE:
                        chunk_to_send = bytes(buffer[:CHUNK_SIZE])
                        buffer = buffer[CHUNK_SIZE:]

                        logger.debug(
                            f"Streaming buffered audio chunk: {len(chunk_to_send)} bytes"
                        )
                        await transport.websocket.send_bytes(chunk_to_send)

                # Send any remaining buffered data
                if buffer:
                    logger.debug(
                        f"Streaming final audio chunk: {len(buffer)} bytes"
                    )
                    await transport.websocket.send_bytes(bytes(buffer))

    async def process_audio(self, audio_data: bytes):
        """
        Process audio data when using direct Deepgram.

        Args:
            audio_data: Raw audio bytes from WebSocket
        """
        if not self.use_direct_deepgram:
            logger.warning("process_audio called but not using direct Deepgram")
            return

        if not self.direct_deepgram or not self.direct_deepgram.is_connected:
            logger.error("Direct Deepgram not connected")
            return

        # Enhanced debugging: check if audio has actual content
        import struct
        if len(audio_data) >= 2:
            # Sample first few int16 values
            sample_count = min(100, len(audio_data)//2)
            samples = struct.unpack(f'{sample_count}h', audio_data[:sample_count*2])
            max_val = max(abs(s) for s in samples) if samples else 0
            avg_val = sum(abs(s) for s in samples) / len(samples) if samples else 0

            # Log every 10th chunk or if there's significant audio
            if max_val > 1000 or len(self._audio_buffer) % 10 == 0:
                logger.debug(f"Audio chunk: {len(audio_data)} bytes, max: {max_val}/32768, avg: {avg_val:.0f}")
        else:
            logger.debug(f"Processing audio chunk: {len(audio_data)} bytes")

        # Send audio directly to Deepgram
        await self.direct_deepgram.send_audio(audio_data)
        logger.debug(f"Sent {len(audio_data)} bytes to Deepgram")

    async def finalize_speech(self):
        """
        Finalize speech recognition when using direct Deepgram.
        Tells Deepgram to finalize the current utterance.
        """
        logger.info("🔴 finalize_speech called - user stopped speaking")

        if not self.use_direct_deepgram:
            logger.warning("finalize_speech called but not using direct Deepgram")
            return

        if not self.direct_deepgram or not self.direct_deepgram.is_connected:
            logger.error("Direct Deepgram not connected")
            return

        logger.info("📝 Sending finalize to Deepgram to get final transcription")
        # Send finalize message to Deepgram
        await self.direct_deepgram.finalize()
        logger.info("✅ Finalize sent to Deepgram")

    async def run(self):
        """Run the pipeline."""
        if self.use_direct_deepgram:
            logger.info("Running with direct Deepgram connection")
            # With direct Deepgram, we don't need a pipeline runner
            # Audio is processed directly via process_audio method
            return

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
        if self.use_direct_deepgram:
            logger.info("Stopping direct Deepgram connection...")
            await self.direct_deepgram.disconnect()
            logger.info("Direct Deepgram stopped")
        elif self._task:
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
        # If using direct Deepgram, check different conditions
        if self.use_direct_deepgram:
            return (
                self.direct_deepgram is not None and
                self.llm_service.is_ready
            )

        # Otherwise check normal pipeline conditions
        return (
            self.stt_service.is_ready and
            self.llm_service.is_ready and
            self._pipeline is not None
        )
