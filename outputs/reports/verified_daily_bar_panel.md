# Verified Daily Bar Panel

- panel_build_status: partial
- output_path: outputs/panels/cn_daily_bar_panel.csv
- row_count: 15

| item | status | detail |
|---|---|---|
| eligible_evidence | pass | count=3 |
| panel_build | partial | cross_source_panel_unavailable; tushare_needs_credentials |
| tickers | - | count=3; 000001.SZ, 300750.SZ, 600519.SH |
| date_range | - | 2026-06-29 to 2026-07-03 |
| row_count | - | 15 |
| qlib_minimum_fields | pass | date,ticker,open,high,low,close,volume |
| cross_source_status | warn | unavailable |
| next_action | - | use panel for format/runtime validation only; complete row-level cross-source checks before strategy use. |

## Boundary

- ProviderEvidence is a traceability ledger, not a training dataset.
- The panel is built only from real daily_bars or provider fetches.
- Summary evidence is not expanded into fake daily_bars.
- This is not a recommendation, not a candidate, not a signal, not confidence, not LLM output, and not trading.
