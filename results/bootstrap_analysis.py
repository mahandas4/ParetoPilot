#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BOOTSTRAP_SEED = 20260814
RESAMPLES = 10_000


def as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_median_ci(values: list[float], seed: int) -> list[float]:
    rng = random.Random(seed)
    boot = []
    for _ in range(RESAMPLES):
        sample = [values[rng.randrange(len(values))] for _ in values]
        boot.append(statistics.median(sample))
    return [round(percentile(boot, 0.025), 4), round(percentile(boot, 0.975), 4)]


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(100 * (centre - half), 1), round(100 * (centre + half), 1)]


def load_rows() -> list[dict[str, str]]:
    with (ROOT / "trials.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 600 or any(row["synthetic_example"] != "True" for row in rows):
        raise ValueError("This demo expects exactly 600 clearly marked synthetic rows")
    return rows


def main() -> None:
    rows = load_rows()
    by_system: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)

    systems = {}
    for index, (system, group) in enumerate(by_system.items()):
        correct = sum(as_bool(row["heldout_correct"]) for row in group)
        cq = sum(as_bool(row["cq_synthesis"]) for row in group)
        credits = [float(row["evaluator_credits"]) for row in group]
        systems[system] = {
            "n": len(group),
            "heldout_correct": correct,
            "heldout_rate_pct": correct,
            "heldout_wilson_95_pct": wilson(correct, len(group)),
            "cq_synthesis": cq,
            "cq_rate_pct": cq,
            "cq_wilson_95_pct": wilson(cq, len(group)),
            "credits_median": statistics.median(credits),
            "credits_bootstrap_95": bootstrap_median_ci(credits, BOOTSTRAP_SEED + index),
        }

    a0 = by_system["A0 Full"]
    stratification = {}
    for difficulty in ("easy", "medium", "hard"):
        group = [row for row in a0 if row["difficulty"] == difficulty]
        correct = sum(as_bool(row["heldout_correct"]) for row in group)
        cq = sum(as_bool(row["cq_synthesis"]) for row in group)
        stratification[difficulty] = {
            "n": len(group),
            "heldout_correct": correct,
            "heldout_wilson_95_pct": wilson(correct, len(group)),
            "cq_synthesis": cq,
            "cq_wilson_95_pct": wilson(cq, len(group)),
        }

    paired = {}
    for offset, column in enumerate(("latency_change_pct", "lut_change_pct", "dsp_change_pct", "bram_change_pct")):
        values = [float(row[column]) for row in a0 if row[column].strip()]
        paired[column] = {
            "n": len(values),
            "median_pct": round(statistics.median(values), 4),
            "bootstrap_95_pct": bootstrap_median_ci(values, BOOTSTRAP_SEED + 100 + offset),
        }

    failures = Counter((row["failure_stage"], row["failure_category"]) for row in a0 if row["failure_category"])
    summary = {
        "synthetic_example": False,
        "warning": "FORMAT DEMO ONLY - NOT EXPERIMENTAL EVIDENCE",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_resamples": RESAMPLES,
        "total_trials": len(rows),
        "systems": systems,
        "a0_stratification": stratification,
        "a0_paired_metrics": paired,
        "a0_failure_counts": [
            {"stage": stage, "category": category, "count": count}
            for (stage, category), count in sorted(failures.items())
        ],
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
