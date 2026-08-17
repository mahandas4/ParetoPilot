from __future__ import annotations

import json
import subprocess
import shutil
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path

from .budget import BudgetLedger
from .diagnostics import classify_failure
from .models import Candidate, EvaluationResult, FailureClass, PPAMetrics, TaskSpec, ToolKind
from .sandbox import CommandSandbox, LocalSandbox


class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, candidate: Candidate, tool: ToolKind) -> EvaluationResult:
        raise NotImplementedError


class VitisHLSEvaluator(Evaluator):
    """Runs real Vitis HLS stages in candidate-isolated workspaces."""

    def __init__(self, task: TaskSpec, budget: BudgetLedger, run_root: str | Path,
                 vitis_hls: str = "vitis_hls", sandbox: CommandSandbox | None = None):
        self.task, self.budget = task, budget
        self.run_root = Path(run_root).resolve()
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.vitis_hls = vitis_hls
        self.sandbox = sandbox or LocalSandbox()

    def evaluate(self, candidate: Candidate, tool: ToolKind) -> EvaluationResult:
        self.budget.spend(tool)
        workspace = self._workspace(candidate)
        if tool in self.task.external_commands:
            return self._external(candidate, tool, workspace)
        if tool not in {ToolKind.CSIM, ToolKind.CSYNTH, ToolKind.COSIM}:
            return EvaluationResult(tool, False, 127,
                                    f"No external command configured for {tool.value}",
                                    failure=classify_failure("tool not found", 127))
        if self.sandbox.host_binary_required and shutil.which(self.vitis_hls) is None:
            message = f"{self.vitis_hls} not found; run on a supported x86-64 Linux/Windows host"
            return EvaluationResult(tool, False, 127, message, failure=classify_failure(message, 127))
        tcl_path = workspace / f"run-{tool.value}.tcl"
        tcl_path.write_text(self._tcl(tool), encoding="utf-8")
        return self._run([self.vitis_hls, "-f", str(tcl_path)], workspace, tool)

    def evaluate_heldout(self, candidate: Candidate) -> EvaluationResult:
        if not self.task.heldout_testbench:
            raise ValueError("Task does not define a held-out testbench")
        workspace = self._workspace(candidate, suffix="heldout")
        tcl_path = workspace / "run-heldout.tcl"
        tcl_path.write_text(self._tcl(ToolKind.CSIM, testbench=self.task.heldout_testbench), encoding="utf-8")
        if self.sandbox.host_binary_required and shutil.which(self.vitis_hls) is None:
            message = f"{self.vitis_hls} not found"
            return EvaluationResult(ToolKind.CSIM, False, 127, message, failure=FailureClass.TOOL)
        return self._run([self.vitis_hls, "-f", str(tcl_path)], workspace, ToolKind.CSIM)

    def _workspace(self, candidate: Candidate, suffix: str = "public") -> Path:
        workspace = self.run_root / f"{candidate.id}-{suffix}"
        if not workspace.exists():
            shutil.copytree(self.task.workdir, workspace)
        source_path = (workspace / self.task.source).resolve()
        if workspace not in source_path.parents:
            raise ValueError("Source path escapes the candidate workspace")
        source_path.write_text(candidate.code, encoding="utf-8")
        return workspace

    def _tcl(self, tool: ToolKind, testbench: str | None = None) -> str:
        testbench = testbench or self.task.testbench
        commands = {
            ToolKind.CSIM: "csim_design",
            ToolKind.CSYNTH: "csynth_design",
            ToolKind.COSIM: "csynth_design\ncosim_design -rtl verilog",
        }
        return f"""open_project -reset pp_project
set_top {self.task.top_function}
add_files {self.task.source}
add_files -tb {testbench}
open_solution -reset solution1 -flow_target vivado
set_part {{{self.task.part}}}
create_clock -period {self.task.clock_ns} -name default
config_export -format ip_catalog -rtl verilog
{commands[tool]}
exit
"""

    def _external(self, candidate: Candidate, tool: ToolKind, workspace: Path) -> EvaluationResult:
        values = {"source": str(workspace / self.task.source), "workdir": str(workspace),
                  "top": self.task.top_function, "candidate": candidate.id}
        argv = [part.format_map(values) for part in self.task.external_commands[tool]]
        return self._run(argv, workspace, tool)

    def _run(self, argv: list[str], workspace: Path, tool: ToolKind) -> EvaluationResult:
        started = time.monotonic()
        try:
            process = self.sandbox.run(
                argv, workspace, self.task.timeout_s, {"PARETOPILOT_TOOL": tool.value}
            )
            stdout, stderr, returncode = process.stdout, process.stderr, process.returncode
        except TimeoutError as exc:
            stdout, stderr = "", str(exc)
            returncode = 124
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or "").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stderr += f"\nTool timeout after {self.task.timeout_s}s"
            returncode = 124
        log = (stdout + "\n" + stderr).strip()
        metrics, reports = self._metrics(workspace, tool) if returncode == 0 else (None, ())
        if returncode == 0 and tool in self.task.report_files and metrics is None:
            log = f"{log}\nExpected metrics report was not produced: {self.task.report_files[tool]}".strip()
            returncode = 3
        violation = self._constraint_violation(metrics) if tool in {
            ToolKind.CSYNTH, ToolKind.IMPLEMENT, ToolKind.HARDWARE
        } else None
        if violation:
            log = f"{log}\nParetoPilot constraint violation: {violation}".strip()
            returncode = 2
        return EvaluationResult(
            tool=tool, passed=returncode == 0, returncode=returncode, log=log,
            metrics=metrics, failure=classify_failure(log, returncode),
            duration_s=time.monotonic() - started,
            stdout_sha256=sha256(stdout.encode()).hexdigest(),
            stderr_sha256=sha256(stderr.encode()).hexdigest(), report_paths=reports,
        )

    def _metrics(self, workspace: Path, tool: ToolKind) -> tuple[PPAMetrics | None, tuple[str, ...]]:
        if tool in self.task.report_files:
            path = workspace / self.task.report_files[tool]
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                allowed = PPAMetrics.__dataclass_fields__.keys()
                return PPAMetrics(**{key: raw[key] for key in allowed if key in raw}), (str(path),)
            return None, ()
        reports = tuple(str(path) for path in workspace.glob("pp_project/solution1/syn/report/*_csynth.xml"))
        if not reports:
            return None, ()
        root = ET.parse(reports[0]).getroot()
        def number(path: str, cast=float):
            node = root.find(path)
            if node is None or not node.text or node.text.strip() in {"", "N/A"}:
                return None
            try:
                return cast(float(node.text.strip()))
            except ValueError:
                return None
        metrics = PPAMetrics(
            latency_cycles=number(".//PerformanceEstimates/SummaryOfOverallLatency/Average-caseLatency", int),
            initiation_interval=number(".//PerformanceEstimates/SummaryOfOverallLatency/Interval-min"),
            clock_ns=number(".//PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod"),
            lut=number(".//AreaEstimates/Resources/LUT", int),
            ff=number(".//AreaEstimates/Resources/FF", int),
            dsp=number(".//AreaEstimates/Resources/DSP", int),
            bram=number(".//AreaEstimates/Resources/BRAM_18K"),
            uram=number(".//AreaEstimates/Resources/URAM", int),
        )
        return metrics, reports

    def _constraint_violation(self, metrics: PPAMetrics | None) -> str | None:
        if metrics is None:
            return None
        checks = {
            "max_latency_cycles": metrics.latency_cycles,
            "max_clock_ns": metrics.clock_ns,
            "max_lut": metrics.lut,
            "max_ff": metrics.ff,
            "max_dsp": metrics.dsp,
            "max_bram": metrics.bram,
            "max_uram": metrics.uram,
            "max_power_w": metrics.power_w,
        }
        violations = [
            f"{name}={value} exceeds {self.task.constraints[name]}"
            for name, value in checks.items()
            if value is not None and name in self.task.constraints
            and float(value) > float(self.task.constraints[name])
        ]
        return "; ".join(violations) or None
