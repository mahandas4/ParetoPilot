from __future__ import annotations

import json
from pathlib import Path

from .archive import ParetoArchive
from .budget import BudgetLedger
from .evaluator import Evaluator
from .generator import CandidateGenerator
from .models import Candidate, CandidateRecord, FailureClass, TaskSpec, ToolKind
from .policy import AdaptiveActionPolicy


class ParetoPilot:
    """Correctness-gated search with compound-budget checks and incumbent preservation."""

    def __init__(self, task: TaskSpec, evaluator: Evaluator, generator: CandidateGenerator,
                 budget: BudgetLedger, trace_path: str | Path,
                 policy: AdaptiveActionPolicy | None = None):
        self.task, self.evaluator, self.generator, self.budget = task, evaluator, generator, budget
        self.trace_path = Path(trace_path)
        self.policy = policy or AdaptiveActionPolicy()
        self.archive = ParetoArchive(task)
        self.records: list[CandidateRecord] = []
        self.events: list[dict[str, object]] = []
        self.generation = 0

    def run(self, baseline_code: str) -> CandidateRecord:
        current = self._register(Candidate(baseline_code, None, "provided baseline", 0, "baseline"))
        self._evaluate(current, ToolKind.CSIM, "correctness")
        while not current.csim_correct and self.budget.can_spend(ToolKind.CSIM):
            failure = current.evaluations[ToolKind.CSIM]
            self.generation += 1
            proposals = self.generator.repair(self.task, current.candidate, failure, self.generation)
            current = self._choose_unseen(proposals, "correctness", failure.failure)
            if current is None:
                return self._terminate(self.records[-1], "generator produced no unseen repair")
            self._evaluate(current, ToolKind.CSIM, "correctness")

        if not current.csim_correct:
            return self._terminate(current, "budget exhausted before public correctness")

        current = self._repair_until_verified(current)
        if not current.verified:
            return self._terminate(current, "budget or proposals exhausted before RTL verification")
        self._evaluate_optional_platform(current)
        self.archive.add(current)
        verified_incumbent = current

        optimisation_path = self._complete_candidate_path()
        while self.budget.can_afford_sequence(optimisation_path):
            incumbent = self.archive.incumbent() or verified_incumbent
            before_hv = self.archive.hypervolume()
            self.generation += 1
            proposals = self.generator.optimize(self.task, incumbent, self.generation)
            trial = self._choose_unseen(proposals, "optimisation", FailureClass.NONE)
            if trial is None:
                break
            self._evaluate(trial, ToolKind.CSIM, "optimisation")
            if not trial.csim_correct:
                self._update_optimisation_failure(trial)
                continue
            self._evaluate(trial, ToolKind.CSYNTH, "optimisation")
            if not trial.synthesized:
                self._update_optimisation_failure(trial)
                continue
            self._evaluate(trial, ToolKind.COSIM, "optimisation")
            if not trial.verified:
                self._update_optimisation_failure(trial)
                continue
            self._evaluate_optional_platform(trial)
            added = self.archive.add(trial)
            utility = max(0.0, self.archive.hypervolume() - before_hv)
            self.policy.update("optimisation", FailureClass.NONE, trial.candidate.action,
                               success=added, utility=utility, risky=False)

        return self._terminate(self.archive.incumbent() or verified_incumbent, "normal termination")

    def _update_optimisation_failure(self, record: CandidateRecord) -> None:
        risky = any(
            result.returncode in {124, 137} or result.failure is FailureClass.TOOL
            for result in record.evaluations.values()
        )
        self.policy.update(
            "optimisation", FailureClass.NONE, record.candidate.action,
            success=False, utility=0.0, risky=risky,
        )

    def _complete_candidate_path(self) -> list[ToolKind]:
        path = [ToolKind.CSIM, ToolKind.CSYNTH, ToolKind.COSIM]
        for tool in (ToolKind.IMPLEMENT, ToolKind.HARDWARE):
            if tool in self.task.external_commands:
                path.append(tool)
        return path

    def _evaluate_optional_platform(self, record: CandidateRecord) -> None:
        for tool in (ToolKind.IMPLEMENT, ToolKind.HARDWARE):
            if tool not in self.task.external_commands or not self.budget.can_spend(tool):
                continue
            self._evaluate(record, tool, "platform")
            if not record.evaluations[tool].passed:
                break

    def _repair_until_verified(self, current: CandidateRecord) -> CandidateRecord:
        """Repair failures from either synthesis or RTL co-simulation."""
        while True:
            if not current.csim_correct:
                return current
            if not current.synthesized:
                if not self.budget.can_afford_sequence([ToolKind.CSYNTH, ToolKind.COSIM]):
                    return current
                self._evaluate(current, ToolKind.CSYNTH, "verification")
                if not current.synthesized:
                    repaired = self._repair_after(current, current.evaluations[ToolKind.CSYNTH])
                    if repaired is None:
                        return current
                    current = repaired
                    continue
            if not self.budget.can_spend(ToolKind.COSIM):
                return current
            self._evaluate(current, ToolKind.COSIM, "verification")
            if current.verified:
                return current
            repaired = self._repair_after(current, current.evaluations[ToolKind.COSIM])
            if repaired is None:
                return current
            current = repaired

    def _repair_after(self, parent: CandidateRecord, failure_result) -> CandidateRecord | None:
        if not self.budget.can_afford_sequence([ToolKind.CSIM, ToolKind.CSYNTH, ToolKind.COSIM]):
            return None
        self.generation += 1
        proposals = self.generator.repair(
            self.task, parent.candidate, failure_result, self.generation
        )
        repaired = self._choose_unseen(proposals, "verification-repair", failure_result.failure)
        if repaired is None:
            return None
        self._evaluate(repaired, ToolKind.CSIM, "verification-repair")
        return repaired if repaired.csim_correct else self._repair_public_failure(repaired)

    def _repair_public_failure(self, current: CandidateRecord) -> CandidateRecord:
        while not current.csim_correct and self.budget.can_afford_sequence(
            [ToolKind.CSIM, ToolKind.CSYNTH, ToolKind.COSIM]
        ):
            failure = current.evaluations[ToolKind.CSIM]
            self.generation += 1
            proposals = self.generator.repair(
                self.task, current.candidate, failure, self.generation
            )
            next_record = self._choose_unseen(
                proposals, "verification-repair", failure.failure
            )
            if next_record is None:
                return current
            current = next_record
            self._evaluate(current, ToolKind.CSIM, "verification-repair")
        return current

    def _choose_unseen(self, proposals: list[Candidate], phase: str,
                       failure: FailureClass) -> CandidateRecord | None:
        seen = {record.candidate.id for record in self.records}
        unseen = [candidate for candidate in proposals if candidate.id not in seen]
        if not unseen:
            return None
        if phase == "correctness":
            action_cost = self.budget.costs.get(ToolKind.CSIM, 1)
        else:
            action_cost = sum(
                self.budget.costs.get(tool, 1) for tool in self._complete_candidate_path()
            )
        actions = [(candidate.action, action_cost) for candidate in unseen]
        decision = self.policy.choose(phase, failure, actions)
        selected = next(candidate for candidate in unseen if candidate.action == decision.action)
        self.events.append({"event": "decision", "phase": phase,
                            "failure": failure.value, "estimate": decision.__dict__})
        return self._register(selected)

    def _register(self, candidate: Candidate) -> CandidateRecord:
        record = CandidateRecord(candidate)
        self.records.append(record)
        self.events.append({"event": "candidate", "id": candidate.id,
                            "parent": candidate.parent_id, "generation": candidate.generation,
                            "action": candidate.action, "rationale": candidate.rationale,
                            "source_sha256": __import__("hashlib").sha256(candidate.code.encode()).hexdigest()})
        return record

    def _evaluate(self, record: CandidateRecord, tool: ToolKind, phase: str) -> None:
        result = self.evaluator.evaluate(record.candidate, tool)
        record.evaluations[tool] = result
        risky = result.returncode in {124, 137} or result.failure is FailureClass.TOOL
        if phase != "optimisation":
            self.policy.update(phase, result.failure, record.candidate.action,
                               success=result.passed,
                               utility=1.0 if result.passed else 0.0, risky=risky)
        self.events.append({
            "event": "evaluation", "id": record.candidate.id, "tool": tool.value,
            "passed": result.passed, "returncode": result.returncode,
            "failure": result.failure.value, "duration_s": result.duration_s,
            "metrics": None if result.metrics is None else result.metrics.__dict__,
            "stdout_sha256": result.stdout_sha256, "stderr_sha256": result.stderr_sha256,
            "reports": list(result.report_paths), "budget": self.budget.snapshot(),
        })
        self._write_trace()

    def _terminate(self, winner: CandidateRecord, reason: str) -> CandidateRecord:
        self.events.append({"event": "termination", "reason": reason,
                            "winner": winner.candidate.id, "budget": self.budget.snapshot(),
                            "policy": self.policy.snapshot(),
                            "pareto_2d": [r.candidate.id for r in self.archive.front_2d],
                            "pareto_3d": [r.candidate.id for r in self.archive.front_3d],
                            "hypervolume": self.archive.hypervolume()})
        self._write_trace()
        return winner

    def _write_trace(self) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
