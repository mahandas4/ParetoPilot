from __future__ import annotations

import json
from pathlib import Path

from .models import TaskSpec, ToolKind


def load_task(path: str | Path) -> tuple[TaskSpec, dict[str, object]]:
    config_path = Path(path).resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if "extends" in raw:
        defaults_path = (config_path.parent / raw["extends"]).resolve()
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
        raw = _deep_merge(defaults, {key: value for key, value in raw.items() if key != "extends"})
    root = (config_path.parent / raw.get("workdir", ".")).resolve()
    spec_path = root / raw.get("specification", "spec.md")
    commands = {ToolKind(name): list(command) for name, command in raw.get("external_commands", {}).items()}
    reports = {ToolKind(name): value for name, value in raw.get("report_files", {}).items()}
    task = TaskSpec(
        name=raw["name"], difficulty=raw.get("difficulty", "unknown"),
        top_function=raw["top_function"], source=raw["source"],
        testbench=raw["testbench"], heldout_testbench=raw.get("heldout_testbench"),
        workdir=root,
        specification=spec_path.read_text(encoding="utf-8") if spec_path.exists() else "",
        part=raw["part"], clock_ns=float(raw["clock_ns"]),
        timeout_s=int(raw.get("timeout_s", 900)),
        numerical_tolerance=raw.get("numerical_tolerance"),
        constraints={key: float(value) for key, value in raw.get("constraints", {}).items()},
        device_capacity={key: float(value) for key, value in raw.get("device_capacity", {}).items()},
        baseline_metrics={key: float(value) for key, value in raw.get("baseline_metrics", {}).items()},
        hv_reference=tuple(float(v) for v in raw.get("hv_reference", [1.5, 1.0, 1.3])),  # type: ignore[arg-type]
        external_commands=commands, report_files=reports,
    )
    return task, raw["budget"]


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def load_suite(path: str | Path) -> list[Path]:
    suite_path = Path(path).resolve()
    raw = json.loads(suite_path.read_text(encoding="utf-8"))
    return [(suite_path.parent / task_path).resolve() for task_path in raw["tasks"]]
