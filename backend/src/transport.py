"""WebSocket transport layer for the Jarvis Pipecat pipeline.

This module implements a thin bridge between the FastAPI WebSocket connection
and the Pipecat `PipelineTask`. It deliberately avoids participating directly
in the Pipecat processor chain in order to keep the data flow simple and
avoid subtle lifecycle issues with `StartFrame` propagation.

Data flow:

- WebSocket → `WebSocketTransport.send_audio` → `_input_task_handler`
  → `AudioRawFrame` → `PipelineTask.queue_frame`

- `JarvisPipeline` wires a `PipelineTask` event handler that calls
  `WebSocketTransport.receive_frame` whenever a synthesized `AudioRawFrame`
  reaches the end of the pipeline. The `_output_task_handler` then streams the
  raw bytes back to the browser over the WebSocket.
"""

import asyncio
import uuid
from typing import Optional

from fastapi import WebSocket
from loguru import logger
from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    TTSAudioRawFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.task import PipelineTask


class WebSocketTransport:
    """
    WebSocket transport for the Pipecat pipeline.

    This class is **not** part of the Pipecat processor list. Instead it acts
    as an I/O bridge:

    - Receives raw PCM audio from the browser, converts it to `AudioRawFrame`
      objects, and enqueues them into a `PipelineTask`.
    - Receives `AudioRawFrame` objects from the pipeline (via a callback wired
      in `JarvisPipeline.setup`) and streams the bytes back over the WebSocket.
    """

    def __init__(
        self,
        websocket: WebSocket,
        sample_rate: int = 16000,
        num_channels: int = 1,
        audio_format: str = "s16le",  # Signed 16-bit little-endian PCM
    ):
        """
        Initialize WebSocket transport.

        Args:
            websocket: FastAPI WebSocket connection
            sample_rate: Audio sample rate in Hz (default: 16kHz)
            num_channels: Number of audio channels (default: 1 for mono)
            audio_format: Audio format (default: s16le for PCM 16-bit)
        """

        self.websocket = websocket
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.audio_format = audio_format

        # Queues for audio data
        self._input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._output_queue: asyncio.Queue[Frame] = asyncio.Queue()

        # Background tasks
        self._input_task: Optional[asyncio.Task] = None
        self._output_task: Optional[asyncio.Task] = None
        self._running = False

        # Pipeline task reference (set during setup)
        self._task: Optional[PipelineTask] = None

        logger.info(
            f"WebSocket transport initialized: {sample_rate}Hz, "
            f"{num_channels}ch, {audio_format}"
        )

    async def setup(self, task: PipelineTask):
        """
        Attach the transport to a running `PipelineTask`.

        This is called from `JarvisPipeline.setup` **after** the pipeline and
        task have been created. The transport then uses this task to inject
        audio frames into the pipeline.

        Args:
            task: The `PipelineTask` that will process frames.
        """
        logger.info("WebSocket transport setup")
        self._task = task

    async def start(self):
        """Start the background tasks that move data between WebSocket and pipeline."""
        if self._running:
            return

        self._running = True

        # Start input task (WebSocket → Pipeline)
        self._input_task = asyncio.create_task(self._input_task_handler())

        # Start output task (Pipeline → WebSocket)
        self._output_task = asyncio.create_task(self._output_task_handler())

        logger.info("WebSocket transport started")

    async def stop(self):
        """Stop the transport tasks."""
        if not self._running:
            return

        self._running = False

        # Cancel tasks
        if self._input_task:
            self._input_task.cancel()
            try:
                await self._input_task
            except asyncio.CancelledError:
                pass

        if self._output_task:
            self._output_task.cancel()
            try:
                await self._output_task
            except asyncio.CancelledError:
                pass

        logger.info("WebSocket transport stopped")

    async def cleanup(self):
        """Cleanup resources."""
        await self.stop()

        # Clear queues
        while not self._input_queue.empty():
            try:
                self._input_queue.get_nowait()
            except Exception:  # pragma: no cover - just best-effort cleanup
                break

        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except Exception:  # pragma: no cover
                break

        logger.info("WebSocket transport cleanup complete")

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data from WebSocket to pipeline.

        Args:
            audio_data: Raw audio bytes from WebSocket
        """
        logger.info(f"Received audio data: {len(audio_data)} bytes")

        # Debug: inspect raw samples coming from the client to ensure we're not
        # just receiving silence from the browser.
        try:
            import array

            samples = array.array("h")
            samples.frombytes(audio_data)
            if samples:
                min_sample = min(samples)
                max_sample = max(samples)
            else:
                min_sample = max_sample = 0
            logger.info(
                "Incoming WebSocket audio stats: "
                f"{len(audio_data)} bytes, min={min_sample}, max={max_sample}"
            )
        except Exception as e:  # pragma: no cover - debug-only path
            logger.warning(f"Failed to inspect incoming audio samples: {e}")

        if not self._running:
            logger.info("Transport not running, starting...")
            await self.start()

        # Put audio data in input queue to be converted to frames.
        await self._input_queue.put(audio_data)
        logger.info("Audio data queued for processing")

    async def user_started_speaking(self):
        """
        Signal to the pipeline that the user has started speaking.

        This enqueues a ``UserStartedSpeakingFrame`` which Deepgram can use to
        start metrics and, when VAD is enabled, drive utterance segmentation.
        """
        if not self._task:
            logger.warning(
                "WebSocketTransport.user_started_speaking called before setup; "
                "dropping frame"
            )
            return

        frame = UserStartedSpeakingFrame(emulated=True)
        logger.debug("Queueing UserStartedSpeakingFrame into pipeline")
        await self._task.queue_frame(frame)

    async def user_stopped_speaking(self):
        """
        Signal to the pipeline that the user has stopped speaking.

        This enqueues a ``UserStoppedSpeakingFrame``. Deepgram's STT service
        listens for this frame and calls ``finalize()`` on its WebSocket
        connection, which in turn causes final ``TranscriptionFrame`` results
        to be emitted. Those final transcriptions are what we feed into the
        LLM and TTS.
        """
        if not self._task:
            logger.warning(
                "WebSocketTransport.user_stopped_speaking called before setup; "
                "dropping frame"
            )
            return

        frame = UserStoppedSpeakingFrame(emulated=True)
        logger.debug("Queueing UserStoppedSpeakingFrame into pipeline (finalize STT)")
        await self._task.queue_frame(frame)

    async def _input_task_handler(self):
        """
        Input task handler: WebSocket → Pipeline.

        Reads audio data from input queue and converts to `AudioRawFrame` for
        the pipeline.
        """
        try:
            while self._running:
                try:
                    # Get audio data from queue (with timeout to check _running)
                    audio_data = await asyncio.wait_for(
                        self._input_queue.get(), timeout=0.1
                    )

                    logger.info(f"Processing audio chunk: {len(audio_data)} bytes")

                    # Convert to AudioRawFrame
                    frame = AudioRawFrame(
                        audio=audio_data,
                        sample_rate=self.sample_rate,
                        num_channels=self.num_channels,
                    )

                    # Ensure frame has an ID (some Pipecat versions don't auto-generate)
                    if not hasattr(frame, "id") or frame.id is None:
                        # Generate a unique 32-bit integer ID
                        frame.id = int(uuid.uuid4().int & ((1 << 31) - 1))

                    logger.info(
                        "Sending AudioRawFrame to pipeline: "
                        f"{len(audio_data)} bytes, {self.sample_rate}Hz"
                    )

                    # Send to pipeline task
                    if not self._task:
                        logger.error(
                            "WebSocketTransport has no PipelineTask attached; "
                            "dropping audio frame"
                        )
                    else:
                        await self._task.queue_frame(frame)

                except asyncio.TimeoutError:
                    # Timeout is expected - just continue to check _running
                    continue

                except Exception as e:
                    logger.error(f"Error in input task: {e}")

        except asyncio.CancelledError:  # pragma: no cover - normal shutdown path
            logger.info("Input task cancelled")
            raise

    async def _output_task_handler(self):
        """
        Output task handler: Pipeline → WebSocket.

        Receives `AudioRawFrame` from pipeline and sends to WebSocket as bytes.
        """
        try:
            while self._running:
                try:
                    # Get frame from pipeline (with timeout to check _running)
                    frame = await asyncio.wait_for(
                        self._output_queue.get(), timeout=0.1
                    )

                    frame_type = type(frame).__name__

                    # Duck‑type on presence of an ``audio`` attribute so we work
                    # with any Pipecat audio frame that carries raw PCM bytes,
                    # regardless of the concrete subclass.
                    audio = getattr(frame, "audio", None)

                    if audio is not None:
                        audio_bytes = audio or b""

                        logger.info(
                            "Sending audio frame to WebSocket: "
                            f"type={frame_type}, bytes={len(audio_bytes)}, "
                            f"sample_rate={getattr(frame, 'sample_rate', None)}"
                        )

                        if not audio_bytes:
                            logger.warning(
                                f"Audio frame of type {frame_type} has empty payload"
                            )

                        await self.websocket.send_bytes(audio_bytes)
                    else:
                        logger.debug(
                            "Output queue received non-audio frame, ignoring: "
                            f"type={frame_type}"
                        )

                except asyncio.TimeoutError:
                    # Timeout is expected - just continue to check _running
                    continue

                except Exception as e:
                    logger.error(f"Error in output task: {e}")

        except asyncio.CancelledError:  # pragma: no cover - normal shutdown path
            logger.info("Output task cancelled")
            raise

    async def receive_frame(self, frame: Frame):
        """
        Receive a frame from the pipeline.

        This is called from `JarvisPipeline.setup` via a `PipelineTask`
        event handler whenever a synthesized `AudioRawFrame` reaches the end
        of the pipeline. We enqueue it so the output task can stream it back
        over the WebSocket.
        """
        await self._output_queue.put(frame)


