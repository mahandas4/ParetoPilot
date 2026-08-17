from __future__ import annotations

from dataclasses import dataclass

from .models import ActionEstimate, FailureClass


@dataclass
class _Stats:
    alpha: float = 1.0
    beta: float = 1.0
    utility: float = 1.0
    risk: float = 0.10
    observations: int = 0


class AdaptiveActionPolicy:
    """Online value-per-credit model with auditable probability, utility and risk."""

    def __init__(self, ewma: float = 0.25):
        self.ewma = ewma
        self._stats: dict[tuple[str, str, str], _Stats] = {}

    def _entry(self, phase: str, failure: FailureClass, action: str) -> _Stats:
        return self._stats.setdefault((phase, failure.value, action), _Stats())

    def estimate(self, phase: str, failure: FailureClass, action: str, cost: int) -> ActionEstimate:
        stat = self._entry(phase, failure, action)
        probability = stat.alpha / (stat.alpha + stat.beta)
        utility = max(stat.utility, 1e-6)
        risk = min(max(stat.risk, 0.0), 1.0)
        score = probability * utility / (max(cost, 1) * (1.0 + risk))
        return ActionEstimate(action, probability, utility, risk, cost, score)

    def choose(self, phase: str, failure: FailureClass, actions: list[tuple[str, int]]) -> ActionEstimate:
        if not actions:
            raise ValueError("At least one action is required")
        estimates = [self.estimate(phase, failure, action, cost) for action, cost in actions]
        return max(estimates, key=lambda estimate: (estimate.score, -estimate.cost, estimate.action))

    def update(self, phase: str, failure: FailureClass, action: str, *, success: bool,
               utility: float, risky: bool) -> None:
        stat = self._entry(phase, failure, action)
        if success:
            stat.alpha += 1.0
        else:
            stat.beta += 1.0
        stat.utility = (1.0 - self.ewma) * stat.utility + self.ewma * max(utility, 0.0)
        stat.risk = (1.0 - self.ewma) * stat.risk + self.ewma * float(risky)
        stat.observations += 1

    def snapshot(self) -> dict[str, dict[str, float]]:
        output: dict[str, dict[str, float]] = {}
        for (phase, failure, action), stat in self._stats.items():
            output[f"{phase}:{failure}:{action}"] = {
                "alpha": stat.alpha, "beta": stat.beta, "probability": stat.alpha / (stat.alpha + stat.beta),
                "utility_ewma": stat.utility, "risk_ewma": stat.risk,
                "observations": float(stat.observations),
            }
        return output

