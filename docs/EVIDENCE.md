# Evidence rules

- `tool-runs/` contains isolated candidate sources, Tcl scripts and vendor reports.
- `trace.json` contains lineage, decisions, budgets, parsed metrics and SHA-256 log hashes.
- `llm-audit/` contains exact prompts, model settings and raw provider responses. API keys are never written.
- `winner.cpp` is the selected source; `result.json` is the per-trial summary.
- `trials.jsonl`, `report/trials.csv` and `report/summary.json` provide task- and difficulty-level results.
- `PROVENANCE.json` records the repository SHA when available, tool versions and fixture hashes.

Local held-out tests are useful regression tests but are not called official or hidden organiser
tests. HLS estimates, routed Vivado results and physical board measurements are labelled separately.
No result should be entered into a paper before its raw report exists in the corresponding run tree.
