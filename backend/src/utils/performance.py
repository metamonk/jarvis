"""
Performance monitoring and profiling utilities.

Provides latency tracking, metrics collection, and performance analysis
for the Pipecat pipeline components (STT, LLM, TTS) and API endpoints.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger
import statistics


@dataclass
class LatencyMetrics:
    """Container for latency measurements."""

    operation: str
    latencies: List[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of measurements."""
        return len(self.latencies)

    @property
    def mean(self) -> float:
        """Mean latency in milliseconds."""
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def median(self) -> float:
        """Median latency in milliseconds."""
        return statistics.median(self.latencies) if self.latencies else 0.0

    @property
    def p90(self) -> float:
        """P90 latency in milliseconds."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.9)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def p95(self) -> float:
        """P95 latency in milliseconds."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def p99(self) -> float:
        """P99 latency in milliseconds."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def min(self) -> float:
        """Minimum latency in milliseconds."""
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max(self) -> float:
        """Maximum latency in milliseconds."""
        return max(self.latencies) if self.latencies else 0.0

    def add_measurement(self, latency_ms: float):
        """Add a latency measurement."""
        self.latencies.append(latency_ms)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "operation": self.operation,
            "count": self.count,
            "mean_ms": round(self.mean, 2),
            "median_ms": round(self.median, 2),
            "p90_ms": round(self.p90, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
            "min_ms": round(self.min, 2),
            "max_ms": round(self.max, 2),
        }


class PerformanceMonitor:
    """
    Performance monitoring and profiling system.

    Tracks latency metrics for different operations and provides
    performance analysis and reporting capabilities.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self._metrics: Dict[str, LatencyMetrics] = defaultdict(
            lambda: LatencyMetrics(operation="unknown")
        )
        self._enabled = True
        logger.info("Performance monitor initialized")

    def enable(self):
        """Enable performance monitoring."""
        self._enabled = True
        logger.info("Performance monitoring enabled")

    def disable(self):
        """Disable performance monitoring."""
        self._enabled = False
        logger.info("Performance monitoring disabled")

    @asynccontextmanager
    async def track(self, operation: str):
        """
        Context manager for tracking operation latency.

        Args:
            operation: Name of the operation being tracked

        Yields:
            The latency in milliseconds after completion

        Example:
            >>> async with monitor.track("stt_processing") as latency:
            ...     result = await process_audio()
            ...     print(f"Processing took {latency} ms")
        """
        if not self._enabled:
            yield None
            return

        start_time = time.perf_counter()

        try:
            yield None
        finally:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            # Store metric
            if operation not in self._metrics:
                self._metrics[operation] = LatencyMetrics(operation=operation)

            self._metrics[operation].add_measurement(latency_ms)

            logger.debug(f"{operation}: {latency_ms:.2f}ms")

    def track_sync(self, operation: str):
        """
        Decorator for tracking synchronous function latency.

        Args:
            operation: Name of the operation being tracked

        Example:
            >>> @monitor.track_sync("database_query")
            ... def query_database():
            ...     return db.execute(query)
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)

                start_time = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    end_time = time.perf_counter()
                    latency_ms = (end_time - start_time) * 1000

                    if operation not in self._metrics:
                        self._metrics[operation] = LatencyMetrics(operation=operation)

                    self._metrics[operation].add_measurement(latency_ms)
                    logger.debug(f"{operation}: {latency_ms:.2f}ms")

            return wrapper
        return decorator

    def track_async(self, operation: str):
        """
        Decorator for tracking asynchronous function latency.

        Args:
            operation: Name of the operation being tracked

        Example:
            >>> @monitor.track_async("llm_inference")
            ... async def call_llm():
            ...     return await llm.generate()
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self._enabled:
                    return await func(*args, **kwargs)

                start_time = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    end_time = time.perf_counter()
                    latency_ms = (end_time - start_time) * 1000

                    if operation not in self._metrics:
                        self._metrics[operation] = LatencyMetrics(operation=operation)

                    self._metrics[operation].add_measurement(latency_ms)
                    logger.debug(f"{operation}: {latency_ms:.2f}ms")

            return wrapper
        return decorator

    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics.

        Args:
            operation: Specific operation to get metrics for (optional)

        Returns:
            Dictionary containing performance metrics
        """
        if operation:
            if operation in self._metrics:
                return self._metrics[operation].to_dict()
            return {}

        # Return all metrics
        return {
            op: metrics.to_dict()
            for op, metrics in self._metrics.items()
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Get performance summary across all operations.

        Returns:
            Dictionary containing summary statistics
        """
        all_metrics = self.get_metrics()

        if not all_metrics:
            return {
                "total_operations": 0,
                "total_measurements": 0,
                "operations": []
            }

        total_measurements = sum(m["count"] for m in all_metrics.values())

        return {
            "total_operations": len(all_metrics),
            "total_measurements": total_measurements,
            "operations": all_metrics,
        }

    def check_targets(self, targets: Dict[str, float]) -> Dict[str, Any]:
        """
        Check if performance metrics meet target thresholds.

        Args:
            targets: Dictionary mapping operation names to target P90 latency in ms

        Returns:
            Dictionary with pass/fail status for each target

        Example:
            >>> results = monitor.check_targets({
            ...     "stt_processing": 100,
            ...     "llm_inference": 300,
            ...     "tts_generation": 100
            ... })
        """
        results = {}

        for operation, target_ms in targets.items():
            if operation in self._metrics:
                metrics = self._metrics[operation]
                p90 = metrics.p90
                passed = p90 <= target_ms

                results[operation] = {
                    "target_ms": target_ms,
                    "actual_p90_ms": round(p90, 2),
                    "passed": passed,
                    "difference_ms": round(p90 - target_ms, 2),
                }
            else:
                results[operation] = {
                    "target_ms": target_ms,
                    "actual_p90_ms": None,
                    "passed": False,
                    "error": "No measurements recorded"
                }

        return results

    def reset(self, operation: Optional[str] = None):
        """
        Reset metrics.

        Args:
            operation: Specific operation to reset (optional, resets all if None)
        """
        if operation:
            if operation in self._metrics:
                del self._metrics[operation]
                logger.info(f"Reset metrics for {operation}")
        else:
            self._metrics.clear()
            logger.info("Reset all metrics")

    def log_summary(self):
        """Log performance summary to logger."""
        summary = self.get_summary()

        logger.info("=" * 60)
        logger.info("PERFORMANCE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Operations: {summary['total_operations']}")
        logger.info(f"Total Measurements: {summary['total_measurements']}")
        logger.info("")

        for operation, metrics in summary["operations"].items():
            logger.info(f"{operation}:")
            logger.info(f"  Count: {metrics['count']}")
            logger.info(f"  Mean: {metrics['mean_ms']}ms")
            logger.info(f"  Median: {metrics['median_ms']}ms")
            logger.info(f"  P90: {metrics['p90_ms']}ms")
            logger.info(f"  P95: {metrics['p95_ms']}ms")
            logger.info(f"  P99: {metrics['p99_ms']}ms")
            logger.info(f"  Min: {metrics['min_ms']}ms")
            logger.info(f"  Max: {metrics['max_ms']}ms")
            logger.info("")

        logger.info("=" * 60)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
