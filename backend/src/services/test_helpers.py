"""Test helpers for Pipecat service testing."""
import asyncio
from typing import AsyncIterator, List
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, EndFrame
from pipecat.transports.base_transport import BaseTransport, TransportParams
from loguru import logger


class QueueTransport(BaseTransport):
    """
    Simple queue-based transport for testing.
    Collects output frames into a queue for testing purposes.
    """

    def __init__(self, params: TransportParams = TransportParams()):
        """Initialize queue transport."""
        super().__init__(params)
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_frames: List[Frame] = []

    async def send_frame(self, frame: Frame):
        """Collect output frame."""
        self.output_frames.append(frame)
        logger.debug(f"Collected frame: {type(frame).__name__}")

    async def receive_frame(self) -> Frame:
        """Get frame from input queue."""
        return await self.input_queue.get()

    async def run(self):
        """Run transport (no-op for testing)."""
        pass


async def run_processor_with_input(
    processor,
    input_frame: Frame,
    timeout: float = 10.0
) -> List[Frame]:
    """
    Run a Pipecat processor with an input frame and collect outputs.

    Args:
        processor: Pipecat processor to test
        input_frame: Input frame to process
        timeout: Maximum time to wait for processing

    Returns:
        List of output frames
    """
    transport = QueueTransport()

    # Create pipeline
    pipeline = Pipeline([processor, transport.output_processor])

    # Create task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=False,
            enable_metrics=False
        )
    )

    # Add input frame to queue
    await transport.input_queue.put(input_frame)
    await transport.input_queue.put(EndFrame())

    # Run pipeline with timeout
    try:
        await asyncio.wait_for(task.run(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Processor test timed out after {timeout}s")

    return transport.output_frames


async def collect_frames_from_iterator(
    frame_iterator: AsyncIterator[Frame],
    timeout: float = 10.0
) -> List[Frame]:
    """
    Collect frames from an async iterator with timeout.

    Args:
        frame_iterator: Async iterator yielding frames
        timeout: Maximum time to wait

    Returns:
        List of collected frames
    """
    frames = []

    try:
        async with asyncio.timeout(timeout):
            async for frame in frame_iterator:
                frames.append(frame)
    except asyncio.TimeoutError:
        logger.warning(f"Frame collection timed out after {timeout}s")
    except Exception as e:
        logger.error(f"Error collecting frames: {e}")

    return frames
