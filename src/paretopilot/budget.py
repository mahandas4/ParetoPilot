from __future__ import annotations

from dataclasses import dataclass, field

from .models import ToolKind


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class BudgetLedger:
    limits: dict[ToolKind, int]
    costs: dict[ToolKind, int]
    unified_limit: int | None = None
    used: dict[ToolKind, int] = field(init=False)
    credits_used: int = 0

    def __post_init__(self) -> None:
        self.used = {kind: 0 for kind in ToolKind}
        for kind in ToolKind:
            if self.limits.get(kind, 0) < 0:
                raise ValueError("Tool limits must be non-negative")
            if self.costs.get(kind, 1) <= 0:
                raise ValueError("Tool costs must be positive")

    def can_spend(self, kind: ToolKind) -> bool:
        if self.used[kind] >= self.limits.get(kind, 0):
            return False
        cost = self.costs.get(kind, 1)
        return self.unified_limit is None or self.credits_used + cost <= self.unified_limit

    def can_afford_sequence(self, sequence: list[ToolKind] | tuple[ToolKind, ...]) -> bool:
        projected_used = dict(self.used)
        projected_credits = self.credits_used
        for kind in sequence:
            if projected_used[kind] >= self.limits.get(kind, 0):
                return False
            projected_used[kind] += 1
            projected_credits += self.costs.get(kind, 1)
            if self.unified_limit is not None and projected_credits > self.unified_limit:
                return False
        return True

    def spend(self, kind: ToolKind) -> None:
        if not self.can_spend(kind):
            raise BudgetExhausted(f"No budget remaining for {kind.value}")
        self.used[kind] += 1
        self.credits_used += self.costs.get(kind, 1)

    def snapshot(self) -> dict[str, object]:
        remaining = {kind.value: max(0, self.limits.get(kind, 0) - self.used[kind])
                     for kind in ToolKind}
        return {
            "calls_used": {kind.value: count for kind, count in self.used.items()},
            "calls_remaining": remaining,
            "credits_used": self.credits_used,
            "credits_remaining": None if self.unified_limit is None else
            max(0, self.unified_limit - self.credits_used),
        }

