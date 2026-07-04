# Qlib Runtime Read Validation

- qlib_runtime_read: dependency_missing
- qlib_available: False
- panel_readable: True
- rows_read: 15

| item | status | detail |
|---|---|---|
| panel_exists | pass | outputs/panels/cn_daily_bar_panel.csv |
| panel_schema | pass | required=date,ticker,open,high,low,close,volume; missing=none |
| panel_shape | pass | rows=15; tickers=3; date_range=2026-06-29 to 2026-07-03 |
| traceability_fields | pass | required=provider_evidence_id,quality_flags,cross_source_status; missing=none |
| qlib_dependency | warn | installed=False; version=- |
| qlib_runtime_read | dependency_missing | qlib_dependency_missing |
| next_action | - | install Qlib only if explicitly approved; then rerun runtime read validation. |

## Boundary

- Does not install Qlib.
- Does not download Qlib data.
- Does not initialize Qlib workflows.
- Does not train models.
- Does not run backtests.
- Does not generate CandidateEvidence.
- Does not generate recommendations, final signals, confidence, LLM output, or trading actions.
