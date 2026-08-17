# ParetoPilot results

## Files

- `trials.csv`: 600 rows, one per configuration/fixture/seed trial.
- `failure_breakdown.csv`: failure-only view derived from `trials.csv`.
- `llm_usage.csv`: per-trial request, token, and cost accounting.
- `summary.json`: computed counts, rates, medians, and intervals.
- `bootstrap_analysis.py`: standard-library analysis that rebuilds `summary.json`.
- `traces/`: example controller trace.
- `hls_reports/`: reports
- `synthetic_results_preview.xlsx`: formatted summary plus short trial and failure samples for inspection.

## Schema notes

Blank metric cells mean that a paired metric was unavailable for that trial.
All failures remain in the success-rate denominators. LLM calls are recorded but
do not debit the evaluator-credit ledger. 
