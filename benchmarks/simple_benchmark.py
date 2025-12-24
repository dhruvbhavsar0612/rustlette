#!/usr/bin/env python3
"""
Simple benchmark comparison between Rustlette and other frameworks.

This script provides a clear, focused comparison of key performance metrics.
"""

import asyncio
import httpx
import time
import subprocess
import sys
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
import statistics


@dataclass
class FrameworkResult:
    name: str
    requests_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    memory_mb: float
    success_rate: float


class SimpleBenchmark:
    def __init__(self):
        self.test_duration = 15  # seconds
        self.concurrent_clients = 20
        self.warmup_time = 2

        self.frameworks = {
            "rustlette": {"port": 8000, "script": "rustlette_app.py"},
            "starlette": {"port": 8002, "script": "starlette_app.py"},
            "fastapi": {"port": 8001, "script": "fastapi_app.py"},
            "flask": {"port": 8003, "script": "flask_app.py"},
        }

        # Test endpoints that work reliably across all frameworks
        self.test_endpoints = ["/", "/health", "/json", "/text"]

    async def load_test_endpoint(
        self, base_url: str, endpoint: str
    ) -> Tuple[List[float], int, int]:
        """Run load test on a single endpoint."""
        latencies = []
        success_count = 0
        error_count = 0

        semaphore = asyncio.Semaphore(self.concurrent_clients)

        async def make_request(client):
            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.get(f"{base_url}{endpoint}", timeout=5.0)
                    end = time.perf_counter()

                    latency_ms = (end - start) * 1000

                    if response.status_code == 200:
                        return latency_ms
                    else:
                        return None
                except:
                    return None

        async with httpx.AsyncClient() as client:
            # Warmup
            for _ in range(5):
                try:
                    await client.get(f"{base_url}/health", timeout=2.0)
                except:
                    pass

            await asyncio.sleep(self.warmup_time)

            # Main test
            start_time = time.time()
            tasks = []

            while time.time() - start_time < self.test_duration:
                # Create batch of concurrent requests
                batch = [make_request(client) for _ in range(self.concurrent_clients)]
                results = await asyncio.gather(*batch, return_exceptions=True)

                for result in results:
                    if isinstance(result, float):
                        latencies.append(result)
                        success_count += 1
                    else:
                        error_count += 1

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)

        return latencies, success_count, error_count

    async def benchmark_framework(self, name: str, config: dict) -> FrameworkResult:
        """Benchmark a single framework."""
        port = config["port"]
        script = config["script"]
        base_url = f"http://127.0.0.1:{port}"

        print(f"\n🔧 Starting {name.upper()} server...")

        # Start server
        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            # Wait for server to start
            await asyncio.sleep(3)

            # Verify server is up
            async with httpx.AsyncClient() as client:
                for attempt in range(10):
                    try:
                        response = await client.get(f"{base_url}/health", timeout=2.0)
                        if response.status_code == 200:
                            print(f"✅ {name.upper()} server ready")
                            break
                    except:
                        if attempt == 9:
                            raise Exception(f"Failed to start {name} server")
                        await asyncio.sleep(1)

            # Run benchmarks
            all_latencies = []
            total_success = 0
            total_errors = 0

            print(f"📊 Testing {name.upper()} endpoints...")

            for endpoint in self.test_endpoints:
                print(f"   Testing {endpoint}...")
                latencies, success, errors = await self.load_test_endpoint(
                    base_url, endpoint
                )

                if latencies:
                    all_latencies.extend(latencies)
                    total_success += success
                    total_errors += errors

                    rps = success / self.test_duration
                    avg_lat = statistics.mean(latencies)
                    print(f"      {rps:.1f} RPS, {avg_lat:.1f}ms avg")

            # Calculate overall metrics
            if all_latencies:
                overall_rps = total_success / (
                    self.test_duration * len(self.test_endpoints)
                )
                avg_latency = statistics.mean(all_latencies)
                p95_latency = statistics.quantiles(all_latencies, n=20)[
                    18
                ]  # 95th percentile
                success_rate = (
                    total_success / (total_success + total_errors)
                    if (total_success + total_errors) > 0
                    else 0
                )

                # Get memory usage (simplified)
                try:
                    import psutil

                    proc = psutil.Process(process.pid)
                    memory_mb = proc.memory_info().rss / 1024 / 1024
                except:
                    memory_mb = 0.0

                return FrameworkResult(
                    name=name.upper(),
                    requests_per_second=overall_rps,
                    avg_latency_ms=avg_latency,
                    p95_latency_ms=p95_latency,
                    memory_mb=memory_mb,
                    success_rate=success_rate,
                )
            else:
                return FrameworkResult(name.upper(), 0, 0, 0, 0, 0)

        finally:
            # Clean up server
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
            print(f"🛑 {name.upper()} server stopped")

    def print_results(self, results: List[FrameworkResult]):
        """Print comparison results in a clear format."""
        print("\n" + "=" * 60)
        print("🏆 FRAMEWORK PERFORMANCE COMPARISON")
        print("=" * 60)

        # Sort by RPS
        sorted_results = sorted(
            results, key=lambda x: x.requests_per_second, reverse=True
        )

        print(
            f"\n{'Framework':<12} {'RPS':<8} {'Avg Lat':<8} {'P95 Lat':<8} {'Memory':<8} {'Success':<8}"
        )
        print("-" * 60)

        for i, result in enumerate(sorted_results):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(
                f"{medal} {result.name:<10} "
                f"{result.requests_per_second:>6.0f} "
                f"{result.avg_latency_ms:>6.1f}ms "
                f"{result.p95_latency_ms:>6.1f}ms "
                f"{result.memory_mb:>6.1f}MB "
                f"{result.success_rate:>6.1%}"
            )

        # Performance comparison
        if len(sorted_results) >= 2:
            best = sorted_results[0]
            print(f"\n📈 PERFORMANCE ANALYSIS:")

            for result in sorted_results[1:]:
                rps_diff = (
                    (best.requests_per_second - result.requests_per_second)
                    / result.requests_per_second
                ) * 100
                lat_diff = (
                    (result.avg_latency_ms - best.avg_latency_ms) / best.avg_latency_ms
                ) * 100

                print(f"   {best.name} vs {result.name}:")
                print(f"      {rps_diff:+.1f}% faster RPS")
                print(f"      {lat_diff:+.1f}% latency difference")

        # Highlight Rustlette performance
        rustlette_result = next((r for r in results if r.name == "RUSTLETTE"), None)
        if rustlette_result:
            rank = sorted_results.index(rustlette_result) + 1
            print(f"\n🦀 RUSTLETTE PERFORMANCE:")
            print(f"   Rank: #{rank} out of {len(results)}")
            print(f"   RPS: {rustlette_result.requests_per_second:.0f}")
            print(f"   Latency: {rustlette_result.avg_latency_ms:.1f}ms average")
            print(f"   Memory: {rustlette_result.memory_mb:.1f}MB")
            print(f"   Success Rate: {rustlette_result.success_rate:.1%}")

    async def run_comparison(self, frameworks_to_test=None):
        """Run the complete benchmark comparison."""
        print("🚀 Starting Simple Framework Benchmark")
        print(
            f"⚙️  Configuration: {self.concurrent_clients} clients, {self.test_duration}s per test"
        )

        if frameworks_to_test is None:
            frameworks_to_test = list(self.frameworks.keys())

        results = []

        for framework in frameworks_to_test:
            if framework in self.frameworks:
                try:
                    result = await self.benchmark_framework(
                        framework, self.frameworks[framework]
                    )
                    results.append(result)
                except Exception as e:
                    print(f"❌ Failed to benchmark {framework}: {e}")
                    # Add empty result
                    results.append(FrameworkResult(framework.upper(), 0, 0, 0, 0, 0))

        self.print_results(results)

        # Save results
        timestamp = int(time.time())
        filename = f"simple_benchmark_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(
                [
                    {
                        "name": r.name,
                        "requests_per_second": r.requests_per_second,
                        "avg_latency_ms": r.avg_latency_ms,
                        "p95_latency_ms": r.p95_latency_ms,
                        "memory_mb": r.memory_mb,
                        "success_rate": r.success_rate,
                    }
                    for r in results
                ],
                f,
                indent=2,
            )

        print(f"\n💾 Results saved to: {filename}")
        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple framework benchmark")
    parser.add_argument(
        "--frameworks",
        nargs="+",
        choices=["rustlette", "starlette", "fastapi", "flask"],
        help="Frameworks to test",
    )

    args = parser.parse_args()

    benchmark = SimpleBenchmark()

    try:
        await benchmark.run_comparison(args.frameworks)
        print("\n✅ Benchmark completed!")
    except KeyboardInterrupt:
        print("\n🛑 Benchmark interrupted")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
