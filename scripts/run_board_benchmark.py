#!/usr/bin/env python3
"""Aggregate cycle counts emitted by a board-specific runner; never invent measurements."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, help="Executable that returns JSON with passed and cycles")
    parser.add_argument("--output", required=True)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--clock-ns", type=float, required=True)
    args = parser.parse_args()
    samples = []
    for _ in range(args.repetitions):
        result = subprocess.run([args.runner], capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            raise SystemExit(f"board runner failed: {result.stderr}")
        payload = json.loads(result.stdout)
        if not payload.get("passed") or "cycles" not in payload:
            raise SystemExit("board runner must emit {passed:true, cycles:<integer>}")
        samples.append(int(payload["cycles"]))
    metrics = {
        "latency_cycles": int(statistics.median(samples)),
        "clock_ns": args.clock_ns,
        "board_id": args.board_id,
        "repetitions": args.repetitions,
        "latency_cycles_min": min(samples),
        "latency_cycles_max": max(samples),
    }
    Path(args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
