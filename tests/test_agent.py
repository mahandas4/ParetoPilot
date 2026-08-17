from paretopilot.agent import ParetoPilot
from paretopilot.budget import BudgetLedger
from paretopilot.evaluator import Evaluator
from paretopilot.generator import DemonstrationGenerator
from paretopilot.models import EvaluationResult, FailureClass, PPAMetrics, ToolKind


class FakeEvaluator(Evaluator):
    def __init__(self, ledger): self.ledger = ledger
    def evaluate(self, candidate, tool):
        self.ledger.spend(tool)
        wrong = "a[i] - b[i]" in candidate.code
        if tool is ToolKind.CSIM and wrong:
            return EvaluationResult(tool, False, 1, "wrong answer mismatch", failure=FailureClass.FUNCTIONAL)
        metrics = None
        if tool is ToolKind.CSYNTH:
            metrics = PPAMetrics(
                latency_cycles=50 if "PIPELINE" in candidate.code else 100,
                lut=150 if "PIPELINE" in candidate.code else 100,
            )
        return EvaluationResult(tool, True, 0, "pass", metrics=metrics)


def test_end_to_end_correctness_gate_and_optimisation(task, tmp_path):
    baseline = """const int N=16;
void kernel(const int a[N], const int b[N], int out[N]) {
    for (int i = 0; i < N; ++i) out[i] = a[i] - b[i];
}\n"""
    limits = {kind: 0 for kind in ToolKind}
    limits.update({ToolKind.CSIM: 5, ToolKind.CSYNTH: 4, ToolKind.COSIM: 4})
    costs = {kind: 1 for kind in ToolKind}
    ledger = BudgetLedger(limits, costs, unified_limit=13)
    agent = ParetoPilot(task, FakeEvaluator(ledger), DemonstrationGenerator(), ledger, tmp_path/"trace.json")
    winner = agent.run(baseline)
    assert winner.verified
    assert "a[i] + b[i]" in winner.candidate.code
    assert "#pragma HLS PIPELINE II=1" in winner.candidate.code
    assert (tmp_path/"trace.json").exists()
