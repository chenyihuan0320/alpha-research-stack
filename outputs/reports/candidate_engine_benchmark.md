# Candidate Engine Benchmark

- run_id: candidate-engine-benchmark-20260704T120612Z
- generated_at: 2026-07-04T12:06:12.358050+00:00
- allowed_evidence_count: 3

This benchmark does not run AlphaSift, Qlib, vectorbt, LLMs, or trading workflows.

| engine | role | status | supported_inputs | expected_output | integration_cost | accuracy_potential | current_blocker | next_action |
|---|---|---|---|---|---|---|---|---|
| alphasift | candidate_engine_candidate | pending_runtime | ProviderEvidence:daily_bar, strategy_yaml, runtime_dependencies | CandidateEvidence | medium | medium | runtime dependency missing: yaml/PyYAML; input mapping still needs runtime proof | Prepare isolated AlphaSift runtime dependencies and rerun no-LLM validation. |
| qlib | factor_model_research_backbone | blocked_by_panel_data | normalized daily_bar panel, feature store, labels | CandidateEvidence | high | high | Qlib requires panel daily_bars; current ProviderEvidence is summary-level. | Build verified daily_bar panel before Qlib runtime validation. |
| vectorbt_event_baseline | validation_baseline | ready | ProviderEvidence:daily_bar, event_dates | ValidationEvidence | low | baseline | not a discovery engine | Use only as event validation baseline after CandidateEvidence exists. |

## Boundary

- Not run by this benchmark.
- Does not generate CandidateEvidence.
- Does not execute candidate discovery.
- Does not execute validation or backtesting.
- Does not use LLMs.
- Does not provide investment advice or trading instructions.
