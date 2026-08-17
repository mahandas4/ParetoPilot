from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agent import ParetoPilot
from .budget import BudgetLedger
from .evaluator import VitisHLSEvaluator
from .experiment import summarize_trials
from .generator import DemonstrationGenerator, LLMSettings, OpenAICompatibleGenerator
from .models import ToolKind
from .sandbox import ContainerSandbox
from .taskio import load_suite, load_task
from .policy import AdaptiveActionPolicy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ParetoPilot real-tool-ready HLS agent")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("task")
    run.add_argument("--output", default="runs")
    run.add_argument("--generator", choices=("demo", "llm"), default="demo")
    run.add_argument("--endpoint", default=os.getenv("LLM_ENDPOINT", ""))
    run.add_argument("--model", default=os.getenv("LLM_MODEL", ""))
    run.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    run.add_argument("--seed", type=int)
    run.add_argument("--vitis-hls", default=os.getenv("VITIS_HLS", "vitis_hls"))
    run.add_argument("--container-image", default="")
    run.add_argument("--container-engine", choices=("docker", "podman"), default="docker")
    run.add_argument("--heldout", action="store_true")
    suite = sub.add_parser("suite")
    suite.add_argument("suite")
    suite.add_argument("--output", default="runs")
    suite.add_argument("--endpoint", default=os.getenv("LLM_ENDPOINT", ""))
    suite.add_argument("--model", default=os.getenv("LLM_MODEL", ""))
    suite.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    suite.add_argument("--seeds", default="0")
    suite.add_argument("--vitis-hls", default=os.getenv("VITIS_HLS", "vitis_hls"))
    report = sub.add_parser("report")
    report.add_argument("trials")
    report.add_argument("--output", default="reports")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "report":
        print(json.dumps(summarize_trials(args.trials, args.output), indent=2))
        return
    if args.command == "suite":
        _run_suite(args)
        return
    summary = _run_task(args.task, args.output, args.generator, args.endpoint, args.model,
                        args.api_key, args.seed, args.vitis_hls, args.heldout,
                        args.container_image, args.container_engine)
    print(json.dumps(summary, indent=2))


def _run_task(task_path: str | Path, output_root: str | Path, generator_name: str,
              endpoint: str, model: str, api_key: str, seed: int | None,
              vitis_hls: str, heldout: bool, container_image: str = "",
              container_engine: str = "docker",
              policy: AdaptiveActionPolicy | None = None) -> dict[str, object]:
    task, raw_budget = load_task(task_path)
    limits = {ToolKind(name): int(value) for name, value in raw_budget["limits"].items()}
    costs = {ToolKind(name): int(value) for name, value in raw_budget["costs"].items()}
    for kind in ToolKind:
        limits.setdefault(kind, 0)
        costs.setdefault(kind, 1)
    ledger = BudgetLedger(limits, costs, raw_budget.get("unified_limit"))
    output = Path(output_root).resolve() / task.name / f"seed-{seed or 0}"
    sandbox = ContainerSandbox(container_image, container_engine) if container_image else None
    evaluator = VitisHLSEvaluator(task, ledger, output / "tool-runs", vitis_hls, sandbox)
    if generator_name == "llm":
        if not all((endpoint, model, api_key)):
            raise SystemExit("LLM mode requires --endpoint, --model and --api-key")
        generator = OpenAICompatibleGenerator(
            LLMSettings(endpoint, model, api_key, seed=seed), output / "llm-audit")
    else:
        generator = DemonstrationGenerator()
    baseline = (task.workdir / task.source).read_text(encoding="utf-8")
    agent = ParetoPilot(task, evaluator, generator, ledger, output / "trace.json", policy)
    winner = agent.run(baseline)
    output.mkdir(parents=True, exist_ok=True)
    (output / "winner.cpp").write_text(winner.candidate.code, encoding="utf-8")
    heldout_result = evaluator.evaluate_heldout(winner.candidate) if heldout and task.heldout_testbench else None
    synthesis = winner.evaluations.get(ToolKind.CSYNTH)
    ppa = winner.ppa_result
    summary: dict[str, object] = {
        "task": task.name, "difficulty": task.difficulty,
        "winner": winner.candidate.id, "public_verified": winner.verified,
        "heldout_correct": None if heldout_result is None else heldout_result.passed,
        "valid_synthesis": bool(synthesis and synthesis.passed and synthesis.metrics),
        "credits_used": ledger.credits_used,
        "calls_used": ledger.snapshot()["calls_used"],
        "pareto_2d": len(agent.archive.front_2d),
        "pareto_3d": len(agent.archive.front_3d),
        "metric_source": None if ppa is None else ppa.tool.value,
        "metrics": None if not ppa or not ppa.metrics else ppa.metrics.__dict__,
    }
    (output / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _run_suite(args) -> None:
    if not all((args.endpoint, args.model, args.api_key)):
        raise SystemExit("Suite mode requires --endpoint, --model and --api-key")
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    results = []
    shared_policy = AdaptiveActionPolicy()
    for task_path in load_suite(args.suite):
        for seed in seeds:
            results.append(_run_task(
                task_path, args.output, "llm", args.endpoint, args.model, args.api_key,
                seed, args.vitis_hls, True, policy=shared_policy,
            ))
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    trials = output / "trials.jsonl"
    trials.write_text("".join(json.dumps(row) + "\n" for row in results), encoding="utf-8")
    summary = summarize_trials(trials, output / "report")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
