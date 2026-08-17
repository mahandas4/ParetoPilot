from pathlib import Path

import pytest

from paretopilot.models import TaskSpec


@pytest.fixture
def task(tmp_path: Path) -> TaskSpec:
    return TaskSpec(
        name="unit", difficulty="easy", top_function="kernel", source="kernel.cpp",
        testbench="testbench.cpp", heldout_testbench=None, workdir=tmp_path,
        specification="add arrays", part="xc7z020clg400-1", clock_ns=10.0,
        timeout_s=10, numerical_tolerance=0.0, constraints={},
        device_capacity={"lut": 1000, "ff": 2000, "dsp": 100, "bram": 50, "uram": 0},
        baseline_metrics={}, hv_reference=(1.5, 1.0, 1.3),
    )
