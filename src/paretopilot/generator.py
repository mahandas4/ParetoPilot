from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .diagnostics import compact_log
from .models import Candidate, CandidateRecord, EvaluationResult, TaskSpec, ToolKind


class CandidateGenerator(ABC):
    @abstractmethod
    def repair(self, task: TaskSpec, parent: Candidate, result: EvaluationResult,
               generation: int) -> list[Candidate]:
        raise NotImplementedError

    @abstractmethod
    def optimize(self, task: TaskSpec, parent: CandidateRecord, generation: int) -> list[Candidate]:
        raise NotImplementedError


@dataclass(frozen=True)
class LLMSettings:
    endpoint: str
    model: str
    api_key: str
    temperature: float = 0.2
    top_p: float = 0.95
    seed: int | None = None
    proposals: int = 2


class OpenAICompatibleGenerator(CandidateGenerator):
    """OpenAI-compatible chat adapter that records exact prompts and responses."""

    def __init__(self, settings: LLMSettings, audit_dir: str | Path):
        self.settings = settings
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.request_number = 0

    def repair(self, task: TaskSpec, parent: Candidate, result: EvaluationResult,
               generation: int) -> list[Candidate]:
        prompt = self._base_prompt(task, parent.code) + f"""
PHASE: correctness repair
The last {result.tool.value} call failed with class {result.failure.value}.
TOOL LOG:\n{compact_log(result.log)}
Repair correctness only. Preserve the top-level function and interface.
"""
        return self._request(prompt, parent.id, generation, "repair")

    def optimize(self, task: TaskSpec, parent: CandidateRecord, generation: int) -> list[Candidate]:
        result = parent.evaluations.get(ToolKind.CSYNTH)
        prompt = self._base_prompt(task, parent.candidate.code) + f"""
PHASE: PPA optimisation
The source passed C simulation. Current synthesis metrics: {result.metrics if result else None!r}.
Propose conservative HLS transformations, explain the expected latency/resource trade-off,
and preserve bit-accurate behaviour and the complete interface.
"""
        return self._request(prompt, parent.candidate.id, generation, "optimise")

    def _base_prompt(self, task: TaskSpec, code: str) -> str:
        return f"""You are an AMD Vitis HLS engineer. Return strict JSON only:
{{"candidates":[{{"action":"short_action_name","rationale":"...","code":"complete source"}}]}}
Return at most {self.settings.proposals} candidates and never omit source text.
TASK: {task.name}
TOP: {task.top_function}
PART: {task.part}
CLOCK_NS: {task.clock_ns}
TOLERANCE: {task.numerical_tolerance}
CONSTRAINTS: {json.dumps(task.constraints, sort_keys=True)}
SPECIFICATION:\n{task.specification}
CURRENT SOURCE:\n```cpp\n{code}\n```
"""

    def _request(self, prompt: str, parent_id: str, generation: int, fallback_action: str) -> list[Candidate]:
        body: dict[str, object] = {
            "model": self.settings.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "response_format": {"type": "json_object"},
        }
        if self.settings.seed is not None:
            body["seed"] = self.settings.seed
        request_bytes = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.settings.endpoint, data=request_bytes,
            headers={"Authorization": f"Bearer {self.settings.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            response_bytes = response.read()
        payload = json.loads(response_bytes.decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        self.request_number += 1
        audit = {
            "settings": {
                "endpoint": self.settings.endpoint, "model": self.settings.model,
                "temperature": self.settings.temperature, "top_p": self.settings.top_p,
                "seed": self.settings.seed, "proposals": self.settings.proposals,
            },
            "request": body, "prompt_sha256": sha256(prompt.encode()).hexdigest(),
            "raw_response": payload, "response_sha256": sha256(response_bytes).hexdigest(),
        }
        (self.audit_dir / f"llm-{self.request_number:04d}.json").write_text(
            json.dumps(audit, indent=2), encoding="utf-8"
        )
        candidates = []
        for item in parsed.get("candidates", [])[: self.settings.proposals]:
            candidates.append(Candidate(
                code=item["code"], parent_id=parent_id,
                rationale=item.get("rationale", fallback_action), generation=generation,
                action=item.get("action", fallback_action),
            ))
        return candidates


class DemonstrationGenerator(CandidateGenerator):
    """Deterministic local generator for controller tests; never an LLM baseline."""

    def repair(self, task: TaskSpec, parent: Candidate, result: EvaluationResult,
               generation: int) -> list[Candidate]:
        replacements = (
            ("a[i] - b[i]", "a[i] + b[i]", "repair_addition"),
            ("i <= N", "i < N", "repair_bounds"),
            ("float acc = 0.0f", "double acc = 0.0", "repair_precision"),
            ("out[i].last = false", "out[i].last = (i == N - 1)", "repair_tlast"),
        )
        proposals = []
        for old, new, action in replacements:
            if old in parent.code:
                proposals.append(Candidate(parent.code.replace(old, new, 1), parent.id,
                                             f"deterministic {action}", generation, action))
        return proposals

    def optimize(self, task: TaskSpec, parent: CandidateRecord, generation: int) -> list[Candidate]:
        code = parent.candidate.code
        marker = "for (int i = 0; i < N; ++i)"
        if marker in code and "#pragma HLS PIPELINE" not in code:
            changed = code.replace(marker, "#pragma HLS PIPELINE II=1\n    " + marker, 1)
            return [Candidate(changed, parent.candidate.id, "pipeline primary loop", generation, "pipeline")]
        return []
