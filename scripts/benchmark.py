"""Measure routing latency through the Python client (process spawn + Dijkstra + parsing).

Usage: python scripts/benchmark.py [--pairs 1000] [--seed 7]
Run it on your own machine and quote the numbers it prints, not anyone else's.
"""
import argparse
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.metro_client import find_route  # noqa: E402
from api.network import load_stations  # noqa: E402


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    names = [s.name for s in load_stations()]
    rng = random.Random(args.seed)
    find_route(names[0], names[1])  # warm up the OS cache

    latencies, found = [], 0
    for _ in range(args.pairs):
        a, b = rng.sample(names, 2)
        t0 = time.perf_counter()
        result = find_route(a, b, rng.choice(["fastest", "least_interchange"]))
        latencies.append((time.perf_counter() - t0) * 1000)
        found += bool(result.get("found"))

    print(f"stations: {len(names)}  pairs: {args.pairs}  routes found: {found}")
    print(f"latency ms  p50={statistics.median(latencies):.1f}  p95={percentile(latencies, 95):.1f}  "
          f"p99={percentile(latencies, 99):.1f}  max={max(latencies):.1f}")


if __name__ == "__main__":
    main()
