"""Evaluate the agent on eval/questions.json.

Metrics (all computed from your own run, nothing is hard-coded):
  tool accuracy   - the set of tools the agent called equals the expected set
  route accuracy  - for route questions, the stations passed to get_shortest_route resolve to the expected ones
  latency         - end-to-end p50 / p95 per question

Usage: python scripts/eval_agent.py [--limit N]
Requires OPENAI_API_KEY and a built knowledge base (make ingest).
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agent import ask, build_agent  # noqa: E402
from api.stations import resolve  # noqa: E402

QUESTIONS = Path(__file__).resolve().parent.parent / "eval" / "questions.json"


def route_args_correct(tools_used: list[dict], case: dict) -> bool:
    for call in tools_used:
        if call["name"] != "get_shortest_route":
            continue
        src, dst = resolve(call["args"].get("source", "")), resolve(call["args"].get("destination", ""))
        if src.station and dst.station and (src.station.name, dst.station.name) == (case["src"], case["dst"]):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[: args.limit]
    agent = build_agent()

    tool_ok, route_total, route_ok, latencies, misses = 0, 0, 0, [], []
    for case in cases:
        t0 = time.perf_counter()
        out = ask(agent, case["question"])
        latencies.append((time.perf_counter() - t0) * 1000)
        called = {c["name"] for c in out["tools_used"]}
        if called == set(case["expected_tools"]):
            tool_ok += 1
        else:
            misses.append((case["question"], sorted(case["expected_tools"]), sorted(called)))
        if "src" in case:
            route_total += 1
            route_ok += route_args_correct(out["tools_used"], case)

    n = len(cases)
    print(f"questions: {n}")
    print(f"tool accuracy: {tool_ok}/{n} = {100 * tool_ok / n:.1f}%")
    if route_total:
        print(f"route accuracy: {route_ok}/{route_total} = {100 * route_ok / route_total:.1f}%")
    ordered = sorted(latencies)
    print(f"latency ms: p50={statistics.median(latencies):.0f}  p95={ordered[min(n - 1, round(0.95 * (n - 1)))]:.0f}")
    for q, expected, got in misses:
        print(f"MISS: {q!r} expected={expected} got={got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
