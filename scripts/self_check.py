#!/usr/bin/env python3
"""Dependency-free structural checks; run pytest for the full test suite."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paretopilot.archive import dominates, hypervolume
from paretopilot.taskio import load_suite, load_task


def main() -> None:
    paths = load_suite(ROOT / "benchmarks/suite.json")
    assert len(paths) == 10
    difficulties = set()
    for path in paths:
        task, budget = load_task(path)
        difficulties.add(task.difficulty)
        assert (task.workdir / task.source).is_file()
        assert (task.workdir / task.testbench).is_file()
        assert task.heldout_testbench and (task.workdir / task.heldout_testbench).is_file()
        assert budget["unified_limit"] > 0
    assert difficulties == {"easy", "medium", "hard"}
    assert dominates((1.0, 2.0), (1.0, 3.0))
    assert hypervolume([(1.0, 4.0), (3.0, 2.0)], (5.0, 5.0)) == 8.0
    with tempfile.TemporaryDirectory() as directory:
        assert Path(directory).is_dir()
    print("ParetoPilot structural self-check passed for 10 fixtures.")


if __name__ == "__main__":
    main()
