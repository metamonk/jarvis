"""Direct Deepgram implementation to bypass Pipecat issues."""
import asyncio
import os
import certifi
from typing import Optional, Callable
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from loguru import logger


class DirectDeepgramService:
    """Direct Deepgram WebSocket implementation that works."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.connection = None
        self.is_connected = False
        self.on_transcript: Optional[Callable] = None
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._last_interim_transcript = ""
        self._last_interim_time = 0
        self._processed_final_in_session = False
        self._expecting_final = False
        self._reconnecting = False

        # Ensure SSL certificates are configured
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

    async def connect(self, max_retries=3):
        """Establish connection to Deepgram with retries."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting direct Deepgram connection (attempt {attempt + 1}/{max_retries})...")

                self.client = DeepgramClient(self.api_key)

                # Log available methods
                logger.debug(f"Available listen methods: {dir(self.client.listen)}")

                # Use the async WebSocket client with proper version
                if hasattr(self.client.listen, 'asyncwebsocket'):
                    # Use the live transcription WebSocket
                    self.connection = self.client.listen.asyncwebsocket.v('1')
                    logger.info("Using asyncwebsocket v1 connection")
                elif hasattr(self.client.listen, 'asynclive'):
                    self.connection = self.client.listen.asynclive.v('1')
                    logger.info("Using asynclive v1 connection")
                elif hasattr(self.client.listen, 'live'):
                    # Try the newer live API
                    self.connection = self.client.listen.live
                    logger.info("Using live connection (newer API)")
                else:
                    logger.error(f"No async WebSocket method found. Available: {dir(self.client.listen)}")
                    raise RuntimeError("Cannot create async WebSocket connection")

                # Set up event handlers
                self.connection.on(
                    LiveTranscriptionEvents.Open,
                    self._on_open
                )
                self.connection.on(
                    LiveTranscriptionEvents.Transcript,
                    self._on_message
                )
                self.connection.on(
                    LiveTranscriptionEvents.Error,
                    self._on_error
                )
                self.connection.on(
                    LiveTranscriptionEvents.Metadata,
                    self._on_metadata
                )
                self.connection.on(
                    LiveTranscriptionEvents.SpeechStarted,
                    self._on_speech_started
                )
                self.connection.on(
                    LiveTranscriptionEvents.UtteranceEnd,
                    self._on_utterance_end
                )
                self.connection.on(
                    LiveTranscriptionEvents.Close,
                    self._on_close
                )

                logger.info("All event handlers registered")

                # Connection options - using nova-2 which is more stable
                options = LiveOptions(
                    encoding='linear16',
                    language='en-US',
                    model='nova-2',  # Using nova-2 for stability
                    sample_rate=16000,
                    channels=1,
                    smart_format=True,
                    interim_results=True,
                    punctuate=True,
                    vad_events=True,  # Enable VAD events for better speech detection
                    utterance_end_ms=1000  # Wait 1 second of silence for utterance end
                )

                # Start connection
                result = await self.connection.start(options)

                if result:
                    # Wait a bit to ensure connection is established
                    await asyncio.sleep(0.5)
                    if self.is_connected:
                        logger.info("✅ Direct Deepgram connection successful!")
                        # Start keep-alive task
                        self._start_keep_alive()
                        return True
                    else:
                        logger.error("Connection started but not confirmed open")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait before retry
                            continue
                else:
                    logger.error("Failed to start Deepgram connection")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Wait before retry
                        continue

            except Exception as e:
                logger.error(f"Direct Deepgram connection error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
                    continue

        logger.error(f"Failed to connect to Deepgram after {max_retries} attempts")
        return False

    async def _on_open(self, *args, **kwargs):
        """Handle connection open."""
        self.is_connected = True
        logger.info("🎯 Deepgram WebSocket opened successfully!")

    async def _on_error(self, *args, **kwargs):
        """Handle errors."""
        error = kwargs.get('error', 'Unknown error')
        logger.error(f"Deepgram error: {error}")

    async def _on_metadata(self, *args, **kwargs):
        """Handle metadata events."""
        logger.debug(f"Deepgram metadata: {kwargs}")

    async def _on_speech_started(self, *args, **kwargs):
        """Handle speech started events."""
        logger.info("🎤 Speech detected - user started speaking")

    async def _on_utterance_end(self, *args, **kwargs):
        """Handle utterance end events."""
        logger.info("🔚 Utterance ended - final transcript should follow")
        # Mark that we're expecting a final transcript
        self._expecting_final = True

    async def _on_close(self, *args, **kwargs):
        """Handle close events."""
        logger.warning(f"⚠️ Deepgram connection closed unexpectedly: {kwargs}")
        self.is_connected = False
        # Try to reconnect if closed unexpectedly
        if self._keep_alive_task and not self._keep_alive_task.done():
            logger.info("Attempting to reconnect to Deepgram...")
            asyncio.create_task(self.connect(max_retries=1))

    async def _on_message(self, *args, **kwargs):
        """Handle transcription messages."""
        logger.debug(f"📨 _on_message called with args: {args}, kwargs keys: {kwargs.keys() if kwargs else 'None'}")

        try:
            result = kwargs.get('result')
            if not result:
                logger.debug("No result in message")
                return

            logger.debug(f"Result type: {type(result)}, has channel: {hasattr(result, 'channel')}")

            if not hasattr(result, 'channel') or not result.channel:
                logger.debug("No channel in result")
                return

            if not hasattr(result.channel, 'alternatives') or len(result.channel.alternatives) == 0:
                logger.debug("No alternatives in channel")
                return

            transcript = result.channel.alternatives[0].transcript
            is_final = result.is_final if hasattr(result, 'is_final') else False

            logger.debug(f"Transcript: '{transcript}', is_final: {is_final}")

            if transcript:
                logger.info(f"🎤 Transcription (final={is_final}): {transcript}")

                # Store last interim transcript as fallback
                if not is_final:
                    self._last_interim_transcript = transcript
                    self._last_interim_time = asyncio.get_event_loop().time()

                # Call async callback directly since we're in async context
                if self.on_transcript and is_final:
                    logger.info(f"📞 Calling on_transcript callback with final: {transcript}")
                    try:
                        result = await self.on_transcript(transcript)
                        logger.info(f"✅ on_transcript callback completed, result: {result}")
                        # Clear interim after successful final
                        self._last_interim_transcript = ""
                        self._processed_final_in_session = True
                    except Exception as callback_error:
                        logger.error(f"❌ Error in on_transcript callback: {callback_error}")
                        logger.error(f"Callback error type: {type(callback_error).__name__}")
                        import traceback
                        logger.error(f"Callback traceback:\n{traceback.format_exc()}")
                        raise  # Re-raise to be caught by outer except

        except Exception as e:
            logger.error(f"❌ Error processing transcription: {e}, args: {args}, kwargs: {kwargs}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

    async def send_audio(self, audio_data: bytes):
        """Send audio to Deepgram."""
        if self.is_connected and self.connection:
            try:
                # Reset the final flag when starting new audio stream
                # (but only if sufficient time has passed since last session)
                current_time = asyncio.get_event_loop().time()
                if current_time - self._last_interim_time > 3.0:
                    self._processed_final_in_session = False

                # Debug: Check if audio has actual content (not just silence)
                import struct
                if len(audio_data) >= 2:
                    # Sample first few int16 values to check for non-silence
                    samples = struct.unpack(f'{min(100, len(audio_data)//2)}h', audio_data[:min(200, len(audio_data))])
                    max_val = max(abs(s) for s in samples) if samples else 0
                    logger.debug(f"Audio stats: {len(audio_data)} bytes, max amplitude: {max_val}/32768")

                    # Warn if audio appears to be silence
                    if max_val < 100:  # Very low amplitude threshold
                        logger.warning(f"Audio appears to be silence or very quiet (max: {max_val})")

                logger.debug(f"Sending {len(audio_data)} bytes to Deepgram WebSocket")
                await self.connection.send(audio_data)
                logger.debug(f"Successfully sent audio to Deepgram")
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
        else:
            logger.error(f"Cannot send audio: connected={self.is_connected}, connection={self.connection is not None}")

    async def finalize(self):
        """Finalize the current utterance without closing the connection."""
        logger.info("🏁 Deepgram finalize() called - forcing final transcription")
        if self.is_connected and self.connection:
            try:
                # Method 1: Try using the SDK's finalize method if available
                if hasattr(self.connection, 'finalize_utterance'):
                    await self.connection.finalize_utterance()
                    logger.info("✅ Called connection.finalize_utterance()")
                elif hasattr(self.connection, 'finish_stream'):
                    # Some versions use finish_stream
                    await self.connection.finish_stream()
                    logger.info("✅ Called connection.finish_stream()")
                else:
                    # Method 2: Just keep the connection alive and wait for natural timeout
                    # The utterance_end_ms=1000 should trigger after 1 second of no audio
                    logger.info("Waiting for utterance_end_ms timeout to trigger...")
                    await self.connection.keep_alive()

                # Give Deepgram time to process and send final transcript
                await asyncio.sleep(1.5)  # Wait longer than utterance_end_ms

                # FALLBACK: If we have an interim transcript and it's recent, use it
                # BUT only if we haven't already processed a final transcript
                current_time = asyncio.get_event_loop().time()
                if (self._last_interim_transcript and
                    (current_time - self._last_interim_time < 3.0) and
                    not self._processed_final_in_session):
                    logger.warning(f"⚠️ No final transcript received, using last interim: {self._last_interim_transcript}")
                    if self.on_transcript:
                        await self.on_transcript(self._last_interim_transcript)
                        self._last_interim_transcript = ""
                        self._processed_final_in_session = True

                logger.info("✅ Finalize completed (connection remains open)")
            except Exception as e:
                logger.error(f"Error finalizing: {e}")
        else:
            logger.error(f"Cannot finalize: connected={self.is_connected}, connection={self.connection is not None}")

    def _start_keep_alive(self):
        """Start the keep-alive task to prevent Deepgram timeout."""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        logger.info("Started Deepgram keep-alive task")

    async def _keep_alive_loop(self):
        """Send periodic keep-alive messages to Deepgram."""
        try:
            while self.is_connected:
                # Send keep-alive every 8 seconds (well before 10-second timeout)
                await asyncio.sleep(8)
                if self.is_connected and self.connection:
                    try:
                        # Send a keep-alive message to Deepgram
                        await self.connection.keep_alive()
                        logger.debug("Sent keep-alive to Deepgram")
                    except Exception as e:
                        logger.warning(f"Failed to send keep-alive: {e}")
        except asyncio.CancelledError:
            logger.info("Keep-alive task cancelled")
        except Exception as e:
            logger.error(f"Keep-alive loop error: {e}")

    async def disconnect(self):
        """Disconnect from Deepgram."""
        # Stop keep-alive task
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass

        if self.connection:
            try:
                await self.connection.finish()
                self.is_connected = False
                logger.info("Deepgram disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")