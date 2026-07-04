# vectorbt Event Baseline

- validation_run_status: success
- validations_written: 3
- ledger_path: outputs/validation/validation_evidence.jsonl

| item | status | detail |
|---|---|---|
| panel_read | pass | rows=15; tickers=3; date_range=2026-06-29 to 2026-07-03 |
| vectorbt_dependency | warn | installed=False; version=- |
| event_inputs | pass | count=3 |
| validations_written | pass | count=3 |
| boundary | - | not signal/recommendation; ValidationEvidence only |

## Boundary

- ValidationEvidence only; not signal/recommendation.
- Does not run portfolio backtests.
- Does not model trading costs.
- Does not optimize strategy parameters.
- Does not generate final confidence, LLM output, or trading actions.
