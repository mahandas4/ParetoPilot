from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any


class ToolKind(str, Enum):
    CSIM = "csim"
    CSYNTH = "csynth"
    COSIM = "cosim"
    IMPLEMENT = "implement"
    HARDWARE = "hardware"


class FailureClass(str, Enum):
    NONE = "none"
    COMPILE = "compile"
    FUNCTIONAL = "functional"
    NUMERICAL = "numerical"
    DEADLOCK = "deadlock"
    INTERFACE = "interface"
    RESOURCE = "resource"
    TIMING = "timing"
    TOOL = "tool"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PPAMetrics:
    latency_cycles: int | None = None
    initiation_interval: float | None = None
    clock_ns: float | None = None
    lut: int | None = None
    ff: int | None = None
    dsp: int | None = None
    bram: float | None = None
    uram: int | None = None
    power_w: float | None = None
    timing_slack_ns: float | None = None

    def utilisation(self, capacity: dict[str, float]) -> dict[str, float]:
        values = {"lut": self.lut, "ff": self.ff, "dsp": self.dsp,
                  "bram": self.bram, "uram": self.uram}
        return {
            name: float(value) / float(capacity[name])
            for name, value in values.items()
            if value is not None and capacity.get(name, 0) > 0
        }

    def objective_vector(
        self, task: "TaskSpec", baseline: dict[str, float] | None = None
    ) -> tuple[float, ...] | None:
        if self.latency_cycles is None:
            return None
        reference = baseline or task.baseline_metrics
        baseline_latency = max(reference.get("latency_cycles", self.latency_cycles), 1.0)
        util = self.utilisation(task.device_capacity)
        max_util = max(util.values(), default=0.0)
        latency = self.latency_cycles / baseline_latency
        if self.power_w is None:
            return (latency, max_util)
        baseline_power = max(reference.get("power_w", self.power_w), 1e-9)
        return (latency, max_util, self.power_w / baseline_power)


@dataclass(frozen=True)
class EvaluationResult:
    tool: ToolKind
    passed: bool
    returncode: int
    log: str
    metrics: PPAMetrics | None = None
    failure: FailureClass = FailureClass.NONE
    duration_s: float = 0.0
    stdout_sha256: str = ""
    stderr_sha256: str = ""
    report_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Candidate:
    code: str
    parent_id: str | None
    rationale: str
    generation: int
    action: str = "unknown"

    @property
    def id(self) -> str:
        return sha256(self.code.encode("utf-8")).hexdigest()[:16]


@dataclass
class CandidateRecord:
    candidate: Candidate
    evaluations: dict[ToolKind, EvaluationResult] = field(default_factory=dict)

    @property
    def csim_correct(self) -> bool:
        result = self.evaluations.get(ToolKind.CSIM)
        return bool(result and result.passed)

    @property
    def synthesized(self) -> bool:
        result = self.evaluations.get(ToolKind.CSYNTH)
        return bool(result and result.passed and result.metrics)

    @property
    def ppa_result(self) -> EvaluationResult | None:
        """Prefer routed/implemented metrics, falling back to HLS estimates."""
        for tool in (ToolKind.IMPLEMENT, ToolKind.CSYNTH):
            result = self.evaluations.get(tool)
            if result and result.passed and result.metrics:
                return result
        return None

    @property
    def verified(self) -> bool:
        csim = self.evaluations.get(ToolKind.CSIM)
        cosim = self.evaluations.get(ToolKind.COSIM)
        return bool(csim and csim.passed and cosim and cosim.passed)

    @property
    def latest_failure(self) -> FailureClass:
        if not self.evaluations:
            return FailureClass.UNKNOWN
        return next(reversed(self.evaluations.values())).failure

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidate"]["id"] = self.candidate.id
        data["evaluations"] = {kind.value: asdict(value)
                               for kind, value in self.evaluations.items()}
        return data


@dataclass(frozen=True)
class TaskSpec:
    name: str
    difficulty: str
    top_function: str
    source: str
    testbench: str
    heldout_testbench: str | None
    workdir: Path
    specification: str
    part: str
    clock_ns: float
    timeout_s: int
    numerical_tolerance: float | None
    constraints: dict[str, float]
    device_capacity: dict[str, float]
    baseline_metrics: dict[str, float]
    hv_reference: tuple[float, float, float]
    external_commands: dict[ToolKind, list[str]] = field(default_factory=dict)
    report_files: dict[ToolKind, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionEstimate:
    action: str
    probability: float
    utility: float
    risk: float
    cost: int
    score: float
