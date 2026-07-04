# Qlib Data Feasibility

- feasibility_status: partial
- qlib_runtime_ready: no
- eligible_daily_bar_count: 3

| item | status | detail |
|---|---|---|
| eligible_daily_bar_evidence | pass | count=3 |
| required_fields | pass | required=date,ticker,open,high,low,close,volume; available=date, ticker, open, high, low, close, volume, amount; missing=none |
| time_series_panel | warn | complete daily_bars panel missing; current evidence is summary-level |
| multi_ticker_panel | pass | tickers=3 |
| qlib_runtime_ready | block | no |
| next_action | - | build verified daily_bar panel before Qlib runtime validation. |

## Boundary

- Does not run Qlib.
- Does not install Qlib.
- Does not train models.
- Does not generate CandidateEvidence.
- Does not generate recommendations, final signals, confidence, LLM output, or trading actions.
