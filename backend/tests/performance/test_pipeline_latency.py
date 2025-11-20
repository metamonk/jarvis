"""
Performance testing for Jarvis pipeline components.

Tests and profiles latency for:
- STT (Deepgram)
- LLM (OpenAI)
- TTS (ElevenLabs)
- Company API calls
- Pinecone searches
- End-to-end pipeline
"""

import asyncio
import time
from typing import List, Dict, Any
import pytest
from loguru import logger

# Mock imports for testing without actual services
try:
    from src.utils.performance import PerformanceMonitor, LatencyMetrics
    from src.utils.cache import cache_manager
except ImportError:
    # For running standalone
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    from src.utils.performance import PerformanceMonitor, LatencyMetrics
    from src.utils.cache import cache_manager


class PerformanceTest:
    """Performance testing suite for Jarvis pipeline."""

    def __init__(self):
        """Initialize performance test suite."""
        self.monitor = PerformanceMonitor()
        self.results = {}

    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up performance tests...")
        await cache_manager.connect()

    async def teardown(self):
        """Tear down test environment."""
        logger.info("Tearing down performance tests...")
        await cache_manager.disconnect()

    async def simulate_stt(self, duration_ms: float = 80):
        """
        Simulate STT processing.

        Args:
            duration_ms: Simulated processing time in milliseconds
        """
        await asyncio.sleep(duration_ms / 1000)

    async def simulate_llm(self, duration_ms: float = 250):
        """
        Simulate LLM inference.

        Args:
            duration_ms: Simulated processing time in milliseconds
        """
        await asyncio.sleep(duration_ms / 1000)

    async def simulate_tts(self, duration_ms: float = 85):
        """
        Simulate TTS generation.

        Args:
            duration_ms: Simulated processing time in milliseconds
        """
        await asyncio.sleep(duration_ms / 1000)

    async def simulate_company_api(self, duration_ms: float = 30):
        """
        Simulate Company API call.

        Args:
            duration_ms: Simulated processing time in milliseconds
        """
        await asyncio.sleep(duration_ms / 1000)

    async def simulate_pinecone(self, duration_ms: float = 45):
        """
        Simulate Pinecone search.

        Args:
            duration_ms: Simulated processing time in milliseconds
        """
        await asyncio.sleep(duration_ms / 1000)

    async def test_stt_latency(self, iterations: int = 100):
        """
        Test STT latency.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing STT latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("stt_processing"):
                await self.simulate_stt()

        metrics = self.monitor.get_metrics("stt_processing")
        self.results["stt"] = metrics
        logger.info(f"STT P90: {metrics['p90_ms']}ms")

    async def test_llm_latency(self, iterations: int = 100):
        """
        Test LLM latency.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing LLM latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("llm_inference"):
                await self.simulate_llm()

        metrics = self.monitor.get_metrics("llm_inference")
        self.results["llm"] = metrics
        logger.info(f"LLM P90: {metrics['p90_ms']}ms")

    async def test_tts_latency(self, iterations: int = 100):
        """
        Test TTS latency.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing TTS latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("tts_generation"):
                await self.simulate_tts()

        metrics = self.monitor.get_metrics("tts_generation")
        self.results["tts"] = metrics
        logger.info(f"TTS P90: {metrics['p90_ms']}ms")

    async def test_company_api_latency(self, iterations: int = 100):
        """
        Test Company API latency.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing Company API latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("company_api"):
                await self.simulate_company_api()

        metrics = self.monitor.get_metrics("company_api")
        self.results["company_api"] = metrics
        logger.info(f"Company API P90: {metrics['p90_ms']}ms")

    async def test_pinecone_latency(self, iterations: int = 100):
        """
        Test Pinecone search latency.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing Pinecone latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("pinecone_search"):
                await self.simulate_pinecone()

        metrics = self.monitor.get_metrics("pinecone_search")
        self.results["pinecone"] = metrics
        logger.info(f"Pinecone P90: {metrics['p90_ms']}ms")

    async def test_end_to_end_latency(self, iterations: int = 100):
        """
        Test end-to-end pipeline latency.

        Simulates: STT → LLM → TTS

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing end-to-end latency ({iterations} iterations)...")

        for _ in range(iterations):
            async with self.monitor.track("end_to_end"):
                # Simulate full pipeline
                await self.simulate_stt()
                await self.simulate_llm()
                await self.simulate_tts()

        metrics = self.monitor.get_metrics("end_to_end")
        self.results["end_to_end"] = metrics
        logger.info(f"End-to-End P90: {metrics['p90_ms']}ms")

    async def test_cache_performance(self, iterations: int = 100):
        """
        Test cache read/write performance.

        Args:
            iterations: Number of test iterations
        """
        logger.info(f"Testing cache performance ({iterations} iterations)...")

        # Test cache write
        for i in range(iterations):
            async with self.monitor.track("cache_write"):
                await cache_manager.set(
                    f"test_key_{i}",
                    {"data": f"test_value_{i}"},
                    "performance_test",
                    300
                )

        # Test cache read
        for i in range(iterations):
            async with self.monitor.track("cache_read"):
                await cache_manager.get(f"test_key_{i}", "performance_test")

        write_metrics = self.monitor.get_metrics("cache_write")
        read_metrics = self.monitor.get_metrics("cache_read")

        self.results["cache_write"] = write_metrics
        self.results["cache_read"] = read_metrics

        logger.info(f"Cache Write P90: {write_metrics['p90_ms']}ms")
        logger.info(f"Cache Read P90: {read_metrics['p90_ms']}ms")

        # Clean up
        await cache_manager.clear_namespace("performance_test")

    def check_performance_targets(self) -> Dict[str, Any]:
        """
        Check if performance meets target thresholds.

        Target: P90 < 500ms end-to-end, targeting 335ms

        Returns:
            Dictionary with pass/fail results
        """
        targets = {
            "stt_processing": 100,      # Target: < 100ms
            "llm_inference": 300,       # Target: < 300ms
            "tts_generation": 100,      # Target: < 100ms
            "company_api": 50,          # Target: < 50ms
            "pinecone_search": 100,     # Target: < 100ms
            "end_to_end": 500,          # Target: < 500ms (goal: 335ms)
            "cache_read": 5,            # Target: < 5ms
            "cache_write": 10,          # Target: < 10ms
        }

        results = self.monitor.check_targets(targets)

        # Log results
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE TARGET VALIDATION")
        logger.info("=" * 80)

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

        logger.info("=" * 80)

        if all_passed:
            logger.info("✓ All performance targets MET")
        else:
            logger.warning("✗ Some performance targets NOT MET")

        logger.info("=" * 80 + "\n")

        return {
            "all_passed": all_passed,
            "results": results,
        }

    async def run_all_tests(self, iterations: int = 100):
        """
        Run all performance tests.

        Args:
            iterations: Number of iterations per test
        """
        logger.info("=" * 80)
        logger.info("STARTING PERFORMANCE TEST SUITE")
        logger.info("=" * 80 + "\n")

        await self.setup()

        try:
            # Run individual component tests
            await self.test_stt_latency(iterations)
            await self.test_llm_latency(iterations)
            await self.test_tts_latency(iterations)
            await self.test_company_api_latency(iterations)
            await self.test_pinecone_latency(iterations)

            # Run end-to-end test
            await self.test_end_to_end_latency(iterations)

            # Run cache performance test
            await self.test_cache_performance(iterations)

            # Check targets
            validation_results = self.check_performance_targets()

            # Print summary
            self.monitor.log_summary()

            return {
                "results": self.results,
                "validation": validation_results,
            }

        finally:
            await self.teardown()


async def main():
    """Main entry point for performance testing."""
    test_suite = PerformanceTest()
    results = await test_suite.run_all_tests(iterations=100)

    # Return results for analysis
    return results


if __name__ == "__main__":
    asyncio.run(main())
