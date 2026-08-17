from paretopilot.models import FailureClass
from paretopilot.policy import AdaptiveActionPolicy


def test_policy_uses_observed_probability_utility_and_risk():
    policy = AdaptiveActionPolicy(ewma=1.0)
    policy.update("optimisation", FailureClass.NONE, "pipeline", success=True, utility=2.0, risky=False)
    policy.update("optimisation", FailureClass.NONE, "unroll", success=False, utility=0.0, risky=True)
    choice = policy.choose("optimisation", FailureClass.NONE, [("pipeline", 2), ("unroll", 2)])
    assert choice.action == "pipeline"
    assert 0.0 < choice.probability < 1.0
    assert choice.utility == 2.0
    assert choice.risk == 0.0
