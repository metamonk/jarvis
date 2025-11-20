"""
Load testing script using Locust for Jarvis backend.

Simulates realistic user load patterns and measures system performance
under various load conditions.
"""

from locust import HttpUser, task, between, events
import json
import time
from typing import Dict, Any
import random


class JarvisUser(HttpUser):
    """
    Simulated Jarvis user for load testing.

    Simulates realistic usage patterns including:
    - Voice interactions (simulated via API calls)
    - Company data queries
    - Document searches
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts."""
        self.load_ids = ["2314", "2315", "2316"]
        self.equipment_ids = ["FORK-001", "FORK-002", "CONV-001"]
        self.skus = ["SKU-001", "SKU-002", "SKU-003"]

    @task(3)
    def get_load_status(self):
        """Query load status (most common operation)."""
        load_id = random.choice(self.load_ids)

        with self.client.get(
            f"/api/v1/loads/{load_id}",
            catch_response=True,
            name="/api/v1/loads/[id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_inventory(self):
        """Query inventory status."""
        sku = random.choice(self.skus)

        with self.client.get(
            f"/api/v1/inventory/{sku}",
            catch_response=True,
            name="/api/v1/inventory/[sku]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_equipment_status(self):
        """Query equipment status."""
        equipment_id = random.choice(self.equipment_ids)

        with self.client.get(
            f"/api/v1/equipment/{equipment_id}",
            catch_response=True,
            name="/api/v1/equipment/[id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def list_loads(self):
        """List all loads."""
        with self.client.get(
            "/api/v1/loads",
            catch_response=True,
            name="/api/v1/loads"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


# Track P90 latency
latencies = []


@events.request.add_listener
def track_latency(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request latency for P90 calculation."""
    if exception is None:
        latencies.append(response_time)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Calculate and log P90 latency when test stops."""
    if latencies:
        sorted_latencies = sorted(latencies)
        p90_index = int(len(sorted_latencies) * 0.9)
        p90 = sorted_latencies[p90_index]
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[p95_index]
        p99_index = int(len(sorted_latencies) * 0.99)
        p99 = sorted_latencies[p99_index]

        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)
        print(f"Total Requests: {len(latencies)}")
        print(f"Mean Latency: {sum(latencies) / len(latencies):.2f}ms")
        print(f"P90 Latency: {p90:.2f}ms")
        print(f"P95 Latency: {p95:.2f}ms")
        print(f"P99 Latency: {p99:.2f}ms")
        print(f"Min Latency: {min(latencies):.2f}ms")
        print(f"Max Latency: {max(latencies):.2f}ms")
        print("=" * 80)

        # Check if P90 target is met
        target_p90 = 500
        if p90 <= target_p90:
            print(f"✓ P90 target MET ({p90:.2f}ms <= {target_p90}ms)")
        else:
            print(f"✗ P90 target NOT MET ({p90:.2f}ms > {target_p90}ms)")

        # Check if stretch goal is met
        stretch_goal = 335
        if p90 <= stretch_goal:
            print(f"✓ Stretch goal MET ({p90:.2f}ms <= {stretch_goal}ms)")
        else:
            print(f"○ Stretch goal NOT MET ({p90:.2f}ms > {stretch_goal}ms)")

        print("=" * 80 + "\n")


"""
Usage:

# Test with local backend
locust -f load_test.py --host http://localhost:8000

# Test with specific load pattern
locust -f load_test.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m

# Headless mode with report
locust -f load_test.py --host http://localhost:8000 --users 100 --spawn-rate 10 --run-time 10m --headless --html report.html

Load scenarios:
1. Light load: --users 10 --spawn-rate 2
2. Medium load: --users 50 --spawn-rate 5
3. Heavy load: --users 100 --spawn-rate 10
4. Stress test: --users 200 --spawn-rate 20
"""
