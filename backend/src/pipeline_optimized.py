"""
Optimized Pipecat voice pipeline with performance monitoring and caching.

This is an enhanced version of pipeline.py that integrates:
- Performance monitoring for all operations
- Redis caching for frequently accessed data
- Optimized service configurations for low latency
"""

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator
)
from pipecat.frames.frames import EndFrame
from pipecat.transports.base_transport import BaseTransport

from .services import DeepgramSTTService, OpenAILLMService, ElevenLabsTTSService
from .config.settings import settings
from .utils.performance import performance_monitor
from .utils.cache import cache_manager
from loguru import logger
from typing import Optional, List, Dict, Any
import asyncio


class OptimizedJarvisPipeline:
    """
    Optimized voice pipeline orchestrator with performance monitoring.

    Enhancements over base JarvisPipeline:
    - Performance tracking for all operations
    - Redis caching integration
    - Optimized service configurations
    - Detailed metrics and reporting
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel
        enable_caching: bool = True,
        enable_monitoring: bool = True
    ):
        """
        Initialize optimized Jarvis pipeline.

        Args:
            system_prompt: System prompt for the LLM
            voice_id: ElevenLabs voice ID
            enable_caching: Enable Redis caching
            enable_monitoring: Enable performance monitoring
        """
        # Initialize services with optimized configurations
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
        self.enable_caching = enable_caching
        self.enable_monitoring = enable_monitoring

        # Pipeline components
        self._pipeline: Optional[Pipeline] = None
        self._task: Optional[PipelineTask] = None
        self._runner: Optional[PipelineRunner] = None

        # Performance tracking
        self._request_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            f"Optimized Jarvis Pipeline initialized "
            f"(caching={'enabled' if enable_caching else 'disabled'}, "
            f"monitoring={'enabled' if enable_monitoring else 'disabled'})"
        )

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
        logger.info("Setting up optimized Jarvis pipeline...")

        async with performance_monitor.track("pipeline_setup"):
            # Connect to Redis cache if enabled
            if self.enable_caching:
                await cache_manager.connect()
                logger.info("Redis cache connected")

            # Create service instances with optimized settings
            async with performance_monitor.track("stt_service_creation"):
                stt = self.stt_service.create_service(
                    model="nova-2",              # Fastest, high accuracy
                    language="en-US",
                    smart_format=True,
                    interim_results=True         # Progressive transcription
                )

            async with performance_monitor.track("llm_service_creation"):
                llm = self.llm_service.create_service(
                    model="gpt-4-turbo-preview",  # Fast, high quality
                    temperature=0.7,
                    max_tokens=1024,              # Reasonable limit
                    # For even faster responses, consider:
                    # model="gpt-3.5-turbo",
                    # stream=True
                )

            async with performance_monitor.track("tts_service_creation"):
                tts = self.tts_service.create_service(
                    voice_id=self.voice_id,
                    model="eleven_turbo_v2_5",    # Fastest model
                    stability=0.5,
                    similarity_boost=0.75,
                    optimize_streaming_latency=3  # Maximum optimization
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

            logger.info("Optimized pipeline setup complete")

    async def run(self):
        """Run the pipeline with performance monitoring."""
        if not self._task:
            raise RuntimeError("Pipeline not set up. Call setup() first.")

        logger.info("Starting optimized pipeline...")

        try:
            async with performance_monitor.track("pipeline_execution"):
                # Create runner
                self._runner = PipelineRunner()

                # Run the pipeline task
                await self._runner.run(self._task)

                logger.info("Pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise
        finally:
            # Log performance summary if monitoring is enabled
            if self.enable_monitoring:
                self._log_performance_summary()

    async def stop(self):
        """Stop the pipeline gracefully."""
        if self._task:
            logger.info("Stopping optimized pipeline...")

            async with performance_monitor.track("pipeline_shutdown"):
                await self._task.queue_frame(EndFrame())

                # Disconnect from cache
                if self.enable_caching:
                    await cache_manager.disconnect()

            logger.info("Pipeline stopped")

            # Final performance report
            if self.enable_monitoring:
                performance_monitor.log_summary()

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

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dictionary containing performance metrics
        """
        metrics = performance_monitor.get_summary()

        # Add cache metrics
        if self.enable_caching:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (
                (self._cache_hits / total_requests * 100)
                if total_requests > 0
                else 0
            )

            metrics["cache"] = {
                "enabled": True,
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
            }
        else:
            metrics["cache"] = {"enabled": False}

        return metrics

    def check_performance_targets(self) -> Dict[str, Any]:
        """
        Check if performance meets target thresholds.

        Returns:
            Dictionary with pass/fail status for each target
        """
        targets = {
            "stt_processing": 100,
            "llm_inference": 300,
            "tts_generation": 100,
            "pipeline_execution": 500,  # End-to-end target
        }

        results = performance_monitor.check_targets(targets)

        # Log results
        logger.info("=" * 60)
        logger.info("PERFORMANCE TARGET VALIDATION")
        logger.info("=" * 60)

        all_passed = True
        for operation, result in results.items():
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            logger.info(
                f"{operation}: {status} "
                f"(Target: {result['target_ms']}ms, "
                f"Actual P90: {result.get('actual_p90_ms', 'N/A')}ms)"
            )
            if not result["passed"]:
                all_passed = False

        logger.info("=" * 60)

        return {
            "all_passed": all_passed,
            "results": results,
            "metrics": self.get_performance_metrics(),
        }

    def _log_performance_summary(self):
        """Log performance summary for current session."""
        metrics = self.get_performance_metrics()

        logger.info("=" * 60)
        logger.info("SESSION PERFORMANCE SUMMARY")
        logger.info("=" * 60)

        if metrics.get("cache", {}).get("enabled"):
            cache_metrics = metrics["cache"]
            logger.info(f"Cache Hit Rate: {cache_metrics['hit_rate_percent']}%")
            logger.info(f"Cache Hits: {cache_metrics['hits']}")
            logger.info(f"Cache Misses: {cache_metrics['misses']}")
            logger.info("")

        logger.info(f"Total Operations: {metrics['total_operations']}")
        logger.info(f"Total Measurements: {metrics['total_measurements']}")
        logger.info("=" * 60)

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

    @property
    def cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.enable_caching

    @property
    def monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self.enable_monitoring


# Alias for compatibility with testing scripts
JarvisPipeline = OptimizedJarvisPipeline
