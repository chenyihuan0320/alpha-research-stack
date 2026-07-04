# AlphaSift Reuse Validation

- run_at: 2026-07-04T11:36:40.153285+00:00
- reuse_validation_status: local_project_inspected_runtime_not_executed
- local_alphasift_found: True
- local_alphasift_path: references/alphasift
- eligible_provider_evidence_count: 3
- candidate_evidence_written: False

## Blocked Reasons

- missing_runtime_validation

## Local AlphaSift Inspection

- cli_found: True
- console_script_found: True
- input_contract_status: needs_project_runtime_validation
- license_summary: Apache-2.0
- market_support_status: cn_supported_likely_hk_us_unknown
- no_llm_supported: True
- path: references/alphasift
- pyproject_found: True
- readme_found: True
- screen_cli_supported: True

## adapter_input_preview

| ticker | candidate_date | evidence_id | data_domain | gate_status |
|---|---|---|---|---|
| 600519.SH | 2026-07-04 | provider-evidence-20260704T113634Z:600519.SH:daily_bar | daily_bar | warn |
| 000001.SZ | 2026-07-04 | provider-evidence-20260704T113634Z:000001.SZ:daily_bar | daily_bar | warn |
| 300750.SZ | 2026-07-04 | provider-evidence-20260704T113634Z:300750.SZ:daily_bar | daily_bar | warn |

## Next Required Action

Install or run the local AlphaSift project separately and execute `alphasift screen <strategy> --no-llm` only after input files are mapped from ProviderEvidence.

## Boundary

- This report is reuse validation evidence only.
- It is not candidate discovery output.
- It is not a stock recommendation, signal, confidence score, backtest, LLM output, or trading instruction.
