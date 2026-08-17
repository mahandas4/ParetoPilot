from pathlib import Path

from paretopilot.evaluator import VitisHLSEvaluator
from paretopilot.models import ToolKind
from paretopilot.taskio import load_suite, load_task


ROOT = Path(__file__).parents[1]


def test_ten_complete_local_fixtures():
    paths = load_suite(ROOT / "benchmarks/suite.json")
    assert len(paths) == 10
    assert {load_task(path)[0].difficulty for path in paths} == {"easy", "medium", "hard"}
    for path in paths:
        task, _ = load_task(path)
        for name in (task.source, task.testbench, task.heldout_testbench, "spec.md"):
            assert name is not None and (task.workdir / name).is_file()


def test_vitis_order_requires_synthesis_before_cosim(task, tmp_path):
    from paretopilot.budget import BudgetLedger
    limits = {kind: 1 for kind in ToolKind}
    costs = {kind: 1 for kind in ToolKind}
    evaluator = VitisHLSEvaluator(task, BudgetLedger(limits, costs), tmp_path)
    cosim_tcl = evaluator._tcl(ToolKind.COSIM)
    assert cosim_tcl.index("csynth_design") < cosim_tcl.index("cosim_design")
