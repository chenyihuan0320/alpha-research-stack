# Candidate Engine Benchmark

- run_id: candidate-engine-benchmark-20260704T134401Z
- generated_at: 2026-07-04T13:44:01.759931+00:00
- allowed_evidence_count: 3

This benchmark does not run AlphaSift, Qlib, vectorbt, LLMs, or trading workflows.

| engine | role | status | supported_inputs | expected_output | integration_cost | accuracy_potential | current_blocker | next_action |
|---|---|---|---|---|---|---|---|---|
| alphasift | candidate_engine_candidate | pending_runtime | ProviderEvidence:daily_bar, strategy_yaml, runtime_dependencies | CandidateEvidence | medium | medium | runtime dependency missing: yaml/PyYAML; input mapping still needs runtime proof | Prepare isolated AlphaSift runtime dependencies and rerun no-LLM validation. |
| qlib | factor_model_research_backbone | dependency_missing_panel_ready | normalized daily_bar panel, feature store, labels | CandidateEvidence | high | high | Qlib dependency missing, but verified daily_bar panel is readable. | Install Qlib only if approved, then rerun runtime read validation. |
| vectorbt_event_baseline | validation_baseline | baseline_validated | ProviderEvidence:daily_bar, event_dates | ValidationEvidence | low | baseline | ValidationEvidence exists for vectorbt/fallback event baseline: count=3. | Use only as validation evidence; do not treat as candidate discovery or signal. |

## Boundary

- Not run by this benchmark.
- Does not generate CandidateEvidence.
- Does not execute candidate discovery.
- Does not execute validation or backtesting.
- Does not use LLMs.
- Does not provide investment advice or trading instructions.
