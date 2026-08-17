from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def wilson_interval(successes: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def summarize_trials(trial_jsonl: str | Path, output_dir: str | Path) -> dict[str, object]:
    trials = [json.loads(line) for line in Path(trial_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for trial in trials:
        groups[str(trial["difficulty"])].append(trial)
    summary: dict[str, object] = {"total_trials": len(trials), "difficulty": {}}
    for difficulty, rows in sorted(groups.items()):
        correct = sum(bool(row.get("heldout_correct")) for row in rows)
        synthesized = sum(bool(row.get("valid_synthesis")) for row in rows)
        metric_summary = {}
        for name in ("latency_cycles", "initiation_interval", "clock_ns", "lut", "ff",
                     "dsp", "bram", "uram", "power_w", "timing_slack_ns"):
            values = [float(row["metrics"][name]) for row in rows
                      if isinstance(row.get("metrics"), dict)
                      and row["metrics"].get(name) is not None]
            if values:
                ordered = sorted(values)
                quartiles = statistics.quantiles(ordered, n=4, method="inclusive") if len(ordered) > 1 else [ordered[0]] * 3
                metric_summary[name] = {
                    "n": len(ordered), "median": statistics.median(ordered),
                    "q1": quartiles[0], "q3": quartiles[2],
                    "min": ordered[0], "max": ordered[-1],
                }
        summary["difficulty"][difficulty] = {
            "trials": len(rows), "correct": correct,
            "correct_rate": correct / len(rows), "correct_wilson95": wilson_interval(correct, len(rows)),
            "valid_synthesis": synthesized,
            "valid_synthesis_rate": synthesized / len(rows),
            "valid_synthesis_wilson95": wilson_interval(synthesized, len(rows)),
            "credits": [row.get("credits_used") for row in rows],
            "component_metrics": metric_summary,
        }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output / "trials.csv").open("w", newline="", encoding="utf-8") as handle:
        if trials:
            writer = csv.DictWriter(handle, fieldnames=sorted(trials[0]))
            writer.writeheader()
            writer.writerows(trials)
    return summary
