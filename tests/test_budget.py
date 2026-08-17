import pytest

from paretopilot.budget import BudgetExhausted, BudgetLedger
from paretopilot.models import ToolKind


def test_compound_budget_is_atomic():
    ledger = BudgetLedger(
        {ToolKind.CSIM: 2, ToolKind.CSYNTH: 1, ToolKind.COSIM: 1},
        {ToolKind.CSIM: 1, ToolKind.CSYNTH: 4, ToolKind.COSIM: 6}, unified_limit=10,
    )
    assert not ledger.can_afford_sequence([ToolKind.CSIM, ToolKind.CSYNTH, ToolKind.COSIM])
    assert ledger.credits_used == 0
    ledger.spend(ToolKind.CSIM)
    assert ledger.credits_used == 1
    ledger.spend(ToolKind.CSYNTH)
    with pytest.raises(BudgetExhausted):
        ledger.spend(ToolKind.COSIM)
