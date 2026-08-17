# ParetoPilot Real-Tool Project

Correctness-gated agent for FPT'26 [Track A]. It asks an LLM for complete HLS C++
candidates, evaluates them in isolated directories, repairs failures from C simulation, synthesis or
RTL co-simulation, preserves verified incumbents, and keeps a genuine latency-area-power Pareto
archive under per-tool and unified credit limits.

<img width="678" height="1202" alt="Receive broken" src="https://github.com/user-attachments/assets/b9b901af-6668-469d-b1b7-b5c537f0ae31" />

The repo has runnable integration code. Vitis, Vivado,
an LLM endpoint + physical board

## Implemented

| Capability | Implementation |
|---|---|
| Vitis HLS | Real `vitis_hls -f` execution and report parsing |
| Tool order | `csim -> csynth -> cosim`; co-simulation Tcl synthesises before RTL simulation |
| Repair loop | Compilation, public-test, synthesis and co-simulation failures return to the generator |
| Correctness gate | Every changed source must pass C simulation before synthesis |
| Budgeting | Per-tool call limits, unified credits and compound-action feasibility |
| Pareto search | Non-dominated 2-D/3-D archives and exact 2-D/3-D hypervolume |
| Missing power | Separate 2-D archive; no invented power value |
| Action selection | Auditable Beta success probability, EWMA utility/risk and value per credit |
| LLM | OpenAI-compatible endpoint, strict complete-source JSON, exact prompt/response audit |
| Safety | Fresh candidate directories and optional restricted Docker/Podman execution |
| Evaluation | Ten local HLS fixtures, public and held-out tests, three difficulty levels |
| Statistics | Per-trial raw data, difficulty summaries and Wilson 95% intervals |
| FPGA stages | External Vivado implementation and board-test command/report contracts |
| Provenance | Tool versions, Git SHA and SHA-256 benchmark manifest |

## Layout

```text
src/paretopilot/       controller, evaluators, LLM adapter, archive and policy
benchmarks/            ten local task fixtures plus suite.json
tests/                 controller and metrics unit tests
platforms/             implementation/hardware JSON contract
containers/            isolation guidance
scripts/               provenance and physical-cycle aggregation
official_tasks/        import area; deliberately empty of organiser material
docs/                  metric, evidence and reporting rules
```

## Install

Python development works on macOS, Linux or Windows:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
pytest
```

Actual Vitis HLS execution must be performed on a supported AMD host, in this case x86-64 Linux/Windows. Apple-silicon macOS can edit project + call remote service but cannot natively run

Vitis HLS 2024.2.

## Run one real Vitis task

After `vitis_hls` is on `PATH`:

```bash
paretopilot run benchmarks/02_functional_mismatch/task.json \
  --generator llm \
  --endpoint https://YOUR_PROVIDER/v1/chat/completions \
  --model YOUR_MODEL \
  --api-key "$LLM_API_KEY" \
  --seed 0 \
  --heldout
```

The deterministic `--generator demo` option is only a controller smoke test and is always labelled
as such; it is not evidence of LLM performance.

## Run all ten tasks

```bash
paretopilot suite benchmarks/suite.json \
  --endpoint https://YOUR_PROVIDER/v1/chat/completions \
  --model YOUR_MODEL \
  --api-key "$LLM_API_KEY" \
  --seeds 0,1,2,3,4 \
  --output runs
```

This produces 50 task/seed trials, raw tool and LLM traces, local held-out correctness results and a
difficulty-stratified report. Use at least several seeds bc one response per task is not enough
to estimate reliability.

## Container execution

If the system owner provides Vitis container image:

```bash
paretopilot run benchmarks/02_functional_mismatch/task.json \
  --generator llm --endpoint "$LLM_ENDPOINT" --model "$LLM_MODEL" --api-key "$LLM_API_KEY" \
  --container-image LOCAL_VITIS_IMAGE
```

The runtime disables networking, drops capabilities and constrains resources. See
`containers/README.md`; a container is risk reduction, not an absolute security guarantee.

## Real implementation and board measurements

HLS estimates are not routed FPGA results. Configure `external_commands.implement` only after a
provided a complete Vivado project. Configure `external_commands.hardware` only
after a host program can program the board, check known outputs and return hardware cycle counts.
See `platforms/README.md` and its example JSON fragment. ParetoPilot automatically runs configured
platform stages after RTL co-simulation when the ledger allows them.

## Reproducibility

Run this in the exact experiment checkout:

```bash
python scripts/capture_provenance.py
```

Commit `PROVENANCE.json` with the configuration, but never commit API keys. The LLM audit stores the
exact request body, prompt and raw response; each candidate, log and report is hash-linked in
`trace.json`. Read `docs/EVIDENCE.md` before transferring any number into the competition paper.
