#!/usr/bin/env python3
"""
Comprehensive benchmarking script for Rustlette vs other Python web frameworks.

This script tests Rustlette, FastAPI, Starlette, and Flask across various metrics:
- Request throughput (requests per second)
- Response latency (average, P95, P99)
- Memory usage
- CPU usage
- Startup time
- Different endpoint types (JSON, text, path params, etc.)

Usage:
    python benchmark.py
    python benchmark.py --quick  # Quick test with fewer requests
    python benchmark.py --framework rustlette  # Test only one framework
"""

import asyncio
import httpx
import time
import psutil
import subprocess
import sys
import argparse
import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
import threading
import signal
import os


@dataclass
class BenchmarkResult:
    """Results from a single benchmark test."""

    framework: str
    endpoint: str
    total_requests: int
    duration: float
    requests_per_second: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float
    success_rate: float
    errors: int
    memory_usage_mb: float
    cpu_usage_percent: float


@dataclass
class FrameworkConfig:
    """Configuration for a framework under test."""

    name: str
    port: int
    command: List[str]
    startup_time: float = 3.0  # Time to wait for startup


class BenchmarkSuite:
    """Main benchmarking suite for comparing web frameworks."""

    def __init__(
        self, quick_mode: bool = False, target_framework: Optional[str] = None
    ):
        self.quick_mode = quick_mode
        self.target_framework = target_framework

        # Benchmark configuration
        self.base_url_template = "http://127.0.0.1:{port}"
        self.concurrent_clients = 50 if not quick_mode else 10
        self.total_requests = 10000 if not quick_mode else 1000
        self.test_duration = 30 if not quick_mode else 10  # seconds

        # Framework configurations
        self.frameworks = {
            "rustlette": FrameworkConfig(
                name="Rustlette",
                port=8000,
                command=[sys.executable, "rustlette_app.py"],
            ),
            "fastapi": FrameworkConfig(
                name="FastAPI",
                port=8001,
                command=[sys.executable, "fastapi_app.py"],
            ),
            "starlette": FrameworkConfig(
                name="Starlette",
                port=8002,
                command=[sys.executable, "starlette_app.py"],
            ),
            "flask": FrameworkConfig(
                name="Flask",
                port=8003,
                command=[sys.executable, "flask_app.py"],
            ),
        }

        # Test endpoints
        self.endpoints = [
            "/",  # Simple JSON response
            "/health",  # Minimal response
            "/json",  # Complex JSON response
            "/text",  # Plain text response
            "/users/123",  # Path parameter
            "/search?q=test&limit=5",  # Query parameters
            "/heavy",  # CPU-intensive endpoint
        ]

        # POST endpoints (tested separately)
        self.post_endpoints = [
            ("/users", {"name": "Test User", "email": "test@example.com"}),
            ("/echo", {"message": "Hello", "data": [1, 2, 3]}),
        ]

    async def benchmark_endpoint(
        self,
        base_url: str,
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict] = None,
        framework_name: str = "",
    ) -> Tuple[List[float], int, int]:
        """Benchmark a single endpoint with concurrent requests."""
        latencies = []
        errors = 0
        success_count = 0

        semaphore = asyncio.Semaphore(self.concurrent_clients)

        async def make_request(client: httpx.AsyncClient) -> Optional[float]:
            async with semaphore:
                start_time = time.perf_counter()
                try:
                    if method == "GET":
                        response = await client.get(
                            f"{base_url}{endpoint}", timeout=10.0
                        )
                    else:
                        response = await client.post(
                            f"{base_url}{endpoint}", json=json_data, timeout=10.0
                        )

                    end_time = time.perf_counter()
                    latency = (end_time - start_time) * 1000  # Convert to milliseconds

                    if response.status_code < 400:
                        return latency
                    else:
                        return None

                except Exception as e:
                    return None

        # Create HTTP client
        async with httpx.AsyncClient() as client:
            # Warmup
            try:
                await client.get(f"{base_url}/health", timeout=5.0)
            except:
                pass

            # Run benchmark for specified duration
            start_time = time.time()
            tasks = []

            while time.time() - start_time < self.test_duration:
                # Create batch of requests
                batch_size = min(
                    self.concurrent_clients,
                    max(1, int(self.total_requests / (self.test_duration * 10))),
                )

                batch_tasks = [make_request(client) for _ in range(batch_size)]
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                for result in batch_results:
                    if isinstance(result, float):
                        latencies.append(result)
                        success_count += 1
                    else:
                        errors += 1

                # Small delay to prevent overwhelming the server
                await asyncio.sleep(0.01)

        return latencies, success_count, errors

    def get_system_stats(self, pid: int) -> Tuple[float, float]:
        """Get memory and CPU usage for a process."""
        try:
            process = psutil.Process(pid)
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            return memory_mb, cpu_percent
        except:
            return 0.0, 0.0

    @asynccontextmanager
    async def run_framework(self, framework_key: str):
        """Context manager to start and stop a framework server."""
        config = self.frameworks[framework_key]

        print(f"🚀 Starting {config.name} server on port {config.port}...")

        # Start the server process
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        process = subprocess.Popen(
            config.command,
            cwd=os.path.dirname(__file__),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )

        try:
            # Wait for server to start
            await asyncio.sleep(config.startup_time)

            # Verify server is responding
            base_url = self.base_url_template.format(port=config.port)
            max_retries = 10

            for i in range(max_retries):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{base_url}/health", timeout=5.0)
                        if response.status_code == 200:
                            print(f"✅ {config.name} server ready")
                            break
                except:
                    if i == max_retries - 1:
                        raise Exception(f"Failed to connect to {config.name} server")
                    await asyncio.sleep(1)

            yield process, base_url

        finally:
            # Cleanup: terminate the server process
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
                process.wait()

            print(f"🛑 {config.name} server stopped")

    async def benchmark_framework(self, framework_key: str) -> List[BenchmarkResult]:
        """Benchmark all endpoints for a single framework."""
        results = []

        async with self.run_framework(framework_key) as (process, base_url):
            config = self.frameworks[framework_key]

            print(f"\n📊 Benchmarking {config.name}...")
            print(f"   Concurrent clients: {self.concurrent_clients}")
            print(f"   Test duration: {self.test_duration}s per endpoint")

            # Test GET endpoints
            for endpoint in self.endpoints:
                print(f"   Testing GET {endpoint}...")

                latencies, success_count, errors = await self.benchmark_endpoint(
                    base_url, endpoint, "GET", framework_name=config.name
                )

                if latencies:
                    # Calculate statistics
                    avg_latency = statistics.mean(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[
                        18
                    ]  # 95th percentile
                    p99_latency = statistics.quantiles(latencies, n=100)[
                        98
                    ]  # 99th percentile
                    min_latency = min(latencies)
                    max_latency = max(latencies)

                    total_requests = success_count + errors
                    duration = self.test_duration
                    rps = success_count / duration
                    success_rate = (
                        success_count / total_requests if total_requests > 0 else 0
                    )

                    # Get system stats
                    memory_mb, cpu_percent = self.get_system_stats(process.pid)

                    result = BenchmarkResult(
                        framework=config.name,
                        endpoint=endpoint,
                        total_requests=total_requests,
                        duration=duration,
                        requests_per_second=rps,
                        avg_latency=avg_latency,
                        p95_latency=p95_latency,
                        p99_latency=p99_latency,
                        min_latency=min_latency,
                        max_latency=max_latency,
                        success_rate=success_rate,
                        errors=errors,
                        memory_usage_mb=memory_mb,
                        cpu_usage_percent=cpu_percent,
                    )

                    results.append(result)

                    print(
                        f"      RPS: {rps:.1f}, Avg Latency: {avg_latency:.2f}ms, "
                        f"P95: {p95_latency:.2f}ms, Errors: {errors}"
                    )

            # Test POST endpoints
            for endpoint, json_data in self.post_endpoints:
                print(f"   Testing POST {endpoint}...")

                latencies, success_count, errors = await self.benchmark_endpoint(
                    base_url, endpoint, "POST", json_data, config.name
                )

                if latencies:
                    # Calculate statistics (same as above)
                    avg_latency = statistics.mean(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[18]
                    p99_latency = statistics.quantiles(latencies, n=100)[98]
                    min_latency = min(latencies)
                    max_latency = max(latencies)

                    total_requests = success_count + errors
                    duration = self.test_duration
                    rps = success_count / duration
                    success_rate = (
                        success_count / total_requests if total_requests > 0 else 0
                    )

                    memory_mb, cpu_percent = self.get_system_stats(process.pid)

                    result = BenchmarkResult(
                        framework=config.name,
                        endpoint=f"POST {endpoint}",
                        total_requests=total_requests,
                        duration=duration,
                        requests_per_second=rps,
                        avg_latency=avg_latency,
                        p95_latency=p95_latency,
                        p99_latency=p99_latency,
                        min_latency=min_latency,
                        max_latency=max_latency,
                        success_rate=success_rate,
                        errors=errors,
                        memory_usage_mb=memory_mb,
                        cpu_usage_percent=cpu_percent,
                    )

                    results.append(result)

                    print(
                        f"      RPS: {rps:.1f}, Avg Latency: {avg_latency:.2f}ms, "
                        f"P95: {p95_latency:.2f}ms, Errors: {errors}"
                    )

        return results

    def print_summary(self, all_results: Dict[str, List[BenchmarkResult]]):
        """Print a comprehensive summary of benchmark results."""
        print("\n" + "=" * 80)
        print("🏆 BENCHMARK RESULTS SUMMARY")
        print("=" * 80)

        # Overall RPS comparison
        print("\n📈 REQUESTS PER SECOND (Higher is better)")
        print("-" * 60)

        framework_rps = {}
        for framework, results in all_results.items():
            total_rps = sum(r.requests_per_second for r in results)
            avg_rps = total_rps / len(results) if results else 0
            framework_rps[framework] = avg_rps

        # Sort by RPS
        sorted_rps = sorted(framework_rps.items(), key=lambda x: x[1], reverse=True)

        for i, (framework, rps) in enumerate(sorted_rps):
            icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(f"{icon} {framework:12} {rps:8.1f} RPS")

        # Latency comparison
        print("\n⚡ AVERAGE LATENCY (Lower is better)")
        print("-" * 60)

        framework_latency = {}
        for framework, results in all_results.items():
            total_latency = sum(r.avg_latency for r in results)
            avg_latency = total_latency / len(results) if results else 0
            framework_latency[framework] = avg_latency

        # Sort by latency (ascending)
        sorted_latency = sorted(framework_latency.items(), key=lambda x: x[1])

        for i, (framework, latency) in enumerate(sorted_latency):
            icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(f"{icon} {framework:12} {latency:8.2f} ms")

        # Memory usage comparison
        print("\n💾 AVERAGE MEMORY USAGE (Lower is better)")
        print("-" * 60)

        framework_memory = {}
        for framework, results in all_results.items():
            if results:
                total_memory = sum(r.memory_usage_mb for r in results)
                avg_memory = total_memory / len(results)
                framework_memory[framework] = avg_memory

        sorted_memory = sorted(framework_memory.items(), key=lambda x: x[1])

        for i, (framework, memory) in enumerate(sorted_memory):
            icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(f"{icon} {framework:12} {memory:8.1f} MB")

        # Detailed endpoint comparison
        print("\n📊 DETAILED ENDPOINT COMPARISON")
        print("-" * 80)

        # Group results by endpoint
        endpoint_results = {}
        for framework, results in all_results.items():
            for result in results:
                if result.endpoint not in endpoint_results:
                    endpoint_results[result.endpoint] = {}
                endpoint_results[result.endpoint][framework] = result

        for endpoint in sorted(endpoint_results.keys()):
            print(f"\n🔗 {endpoint}")
            endpoint_data = endpoint_results[endpoint]

            # Sort by RPS for this endpoint
            sorted_endpoint = sorted(
                endpoint_data.items(),
                key=lambda x: x[1].requests_per_second,
                reverse=True,
            )

            for i, (framework, result) in enumerate(sorted_endpoint):
                icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
                print(
                    f"  {icon} {framework:12} "
                    f"{result.requests_per_second:6.1f} RPS, "
                    f"{result.avg_latency:6.2f}ms avg, "
                    f"{result.p95_latency:6.2f}ms p95"
                )

        # Summary scores
        print("\n🏆 OVERALL RANKING")
        print("-" * 60)

        # Calculate composite score (RPS weight: 40%, Latency: 30%, Memory: 30%)
        framework_scores = {}

        if framework_rps and framework_latency and framework_memory:
            max_rps = max(framework_rps.values())
            min_latency = min(framework_latency.values())
            min_memory = min(framework_memory.values())

            for framework in all_results.keys():
                rps_score = (framework_rps.get(framework, 0) / max_rps) * 40
                latency_score = (
                    min_latency / framework_latency.get(framework, float("inf"))
                ) * 30
                memory_score = (
                    min_memory / framework_memory.get(framework, float("inf"))
                ) * 30

                total_score = rps_score + latency_score + memory_score
                framework_scores[framework] = total_score

        sorted_scores = sorted(
            framework_scores.items(), key=lambda x: x[1], reverse=True
        )

        for i, (framework, score) in enumerate(sorted_scores):
            icon = "👑" if i == 0 else "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            print(f"{icon} {framework:12} {score:6.1f} points")

    async def run_benchmarks(self):
        """Run benchmarks for all frameworks."""
        print("🚀 Starting Web Framework Benchmarks")
        print("=" * 50)
        print(f"Configuration:")
        print(f"  Mode: {'Quick' if self.quick_mode else 'Full'}")
        print(f"  Concurrent clients: {self.concurrent_clients}")
        print(f"  Test duration per endpoint: {self.test_duration}s")

        if self.target_framework:
            print(f"  Testing only: {self.target_framework}")
            frameworks_to_test = {
                self.target_framework: self.frameworks[self.target_framework]
            }
        else:
            frameworks_to_test = self.frameworks

        all_results = {}

        for framework_key in frameworks_to_test:
            try:
                results = await self.benchmark_framework(framework_key)
                all_results[self.frameworks[framework_key].name] = results
            except Exception as e:
                print(f"❌ Failed to benchmark {framework_key}: {e}")
                all_results[self.frameworks[framework_key].name] = []

        # Print comprehensive summary
        self.print_summary(all_results)

        # Save results to JSON file
        results_data = {}
        for framework, results in all_results.items():
            results_data[framework] = [
                {
                    "endpoint": r.endpoint,
                    "requests_per_second": r.requests_per_second,
                    "avg_latency": r.avg_latency,
                    "p95_latency": r.p95_latency,
                    "p99_latency": r.p99_latency,
                    "memory_usage_mb": r.memory_usage_mb,
                    "success_rate": r.success_rate,
                }
                for r in results
            ]

        timestamp = int(time.time())
        filename = f"benchmark_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(results_data, f, indent=2)

        print(f"\n💾 Results saved to: {filename}")

        return all_results


def main():
    parser = argparse.ArgumentParser(description="Benchmark web frameworks")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark")
    parser.add_argument(
        "--framework",
        choices=["rustlette", "fastapi", "starlette", "flask"],
        help="Test only specific framework",
    )

    args = parser.parse_args()

    # Check if required modules are available
    required_modules = ["httpx", "psutil"]
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print(f"❌ Missing required modules: {', '.join(missing_modules)}")
        print(f"Install with: pip install {' '.join(missing_modules)}")
        return 1

    # Run benchmarks
    suite = BenchmarkSuite(quick_mode=args.quick, target_framework=args.framework)

    try:
        results = asyncio.run(suite.run_benchmarks())
        print("\n✅ Benchmark completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Benchmark interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
