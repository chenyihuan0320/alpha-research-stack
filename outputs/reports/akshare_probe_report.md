# AkShare Provider Probe Report

- 运行时间: 2026-07-03T08:52:26.333360+00:00
- provider: akshare
- akshare_installed: True
- akshare_version: 1.18.64
- akshare_import_error: -
- configured_proxy_mode: auto
- effective_proxy_mode: respect_env_proxy
- daily_bar_retry_mode_summary: respect_env_proxy: success=2, failed=9; direct_no_proxy: success=0, failed=9
- eastmoney_proxy_bypass: False
- eastmoney_proxy_mode: auto
- eastmoney_no_proxy: <local>,eastmoney.com,.eastmoney.com,push2his.eastmoney.com,33.push2his.eastmoney.com
- proxy_env_vars_present_outside_eastmoney_call: HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy
- scope: CN daily_bar, CN valuation_snapshot, HK daily_bar; US skipped
- note: This report is data coverage evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.

## Summary

- success: 5
- failed: 4
- skipped: 3

## Results

| market | ticker | capability | status | rows | coverage_pct | sample_keys | covered_fields | missing_fields | quality_flags | reason |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| CN | 600519.SH | daily_bar | success | 5 | 100.0% | market, ticker, date, open, high, low, close, adj_close, volume, amount, turnover, source, source_updated_at, adjustment, quality_flags | adj_close, adjustment, amount, close, date, high, low, open, turnover, volume | - | adjustment_unverified:qfq, unit_unverified:amount, unit_unverified:turnover, unit_unverified:volume | - |
| CN | 600519.SH | valuation_snapshot | success | 1 | 50.0% | market, ticker, date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield, source, source_updated_at, quality_flags | date, market_cap, pb, pe | dividend_yield, ev_ebitda, fcf_yield, ps | asof_mismatch:market_cap=2026-07-02,pb=2026-07-02,pe=2026-07-03, missing_field:dividend_yield, missing_field:ev_ebitda, missing_field:fcf_yield, missing_field:ps, partial_coverage:dividend_yield, partial_coverage:ev_ebitda, partial_coverage:fcf_yield, partial_coverage:ps, unit_unverified:dividend_yield, unit_unverified:market_cap | - |
| CN | 000001.SZ | daily_bar | failed | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | provider_error | Eastmoney provider call failed for CN daily_bar 000001.SZ; respect_env_proxy failed: AkShare provider call failed for CN daily_bar 000001.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for CN daily_bar 000001.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts |
| CN | 000001.SZ | valuation_snapshot | success | 1 | 50.0% | market, ticker, date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield, source, source_updated_at, quality_flags | date, market_cap, pb, pe | dividend_yield, ev_ebitda, fcf_yield, ps | asof_mismatch:market_cap=2026-07-02,pb=2026-07-03,pe=2026-07-02, missing_field:dividend_yield, missing_field:ev_ebitda, missing_field:fcf_yield, missing_field:ps, partial_coverage:dividend_yield, partial_coverage:ev_ebitda, partial_coverage:fcf_yield, partial_coverage:ps, unit_unverified:dividend_yield, unit_unverified:market_cap | - |
| CN | 300750.SZ | daily_bar | failed | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | provider_error | Eastmoney provider call failed for CN daily_bar 300750.SZ; respect_env_proxy failed: AkShare provider call failed for CN daily_bar 300750.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for CN daily_bar 300750.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts |
| CN | 300750.SZ | valuation_snapshot | success | 1 | 50.0% | market, ticker, date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield, source, source_updated_at, quality_flags | date, market_cap, pb, pe | dividend_yield, ev_ebitda, fcf_yield, ps | missing_field:dividend_yield, missing_field:ev_ebitda, missing_field:fcf_yield, missing_field:ps, partial_coverage:dividend_yield, partial_coverage:ev_ebitda, partial_coverage:fcf_yield, partial_coverage:ps, unit_unverified:dividend_yield, unit_unverified:market_cap | - |
| HK | 0700.HK | daily_bar | failed | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | provider_error | Eastmoney provider call failed for HK daily_bar 0700.HK; respect_env_proxy failed: AkShare provider call failed for HK daily_bar 0700.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for HK daily_bar 0700.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts |
| HK | 9988.HK | daily_bar | failed | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | provider_error | Eastmoney provider call failed for HK daily_bar 9988.HK; respect_env_proxy failed: AkShare provider call failed for HK daily_bar 9988.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for HK daily_bar 9988.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts |
| HK | 3690.HK | daily_bar | success | 5 | 90.0% | market, ticker, date, open, high, low, close, adj_close, volume, amount, turnover, source, source_updated_at, adjustment, quality_flags | adjustment, amount, close, date, high, low, open, turnover, volume | adj_close | adjustment_unverified:none, unit_unverified:amount, unit_unverified:turnover, unit_unverified:volume | - |
| US | AAPL | daily_bar | skipped | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |
| US | NVDA | daily_bar | skipped | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |
| US | MSFT | daily_bar | skipped | 0 | 0.0% | - | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |

## Field Coverage Notes

- `covered_fields` means at least one returned sample row had a non-null value for that contract field.
- `missing_fields` may include fields AkShare does not provide directly, such as `ev_ebitda` or `fcf_yield`.
- `quality_flags` are adapter-level flags generated from contract/provider field mapping.
- `sample_keys` shows the first returned normalized sample row's key names, capped to 20 keys; it does not include full market data.

## Failure Reasons

- CN 000001.SZ daily_bar: Eastmoney provider call failed for CN daily_bar 000001.SZ; respect_env_proxy failed: AkShare provider call failed for CN daily_bar 000001.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for CN daily_bar 000001.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts
- CN 300750.SZ daily_bar: Eastmoney provider call failed for CN daily_bar 300750.SZ; respect_env_proxy failed: AkShare provider call failed for CN daily_bar 300750.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for CN daily_bar 300750.SZ: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts
- HK 0700.HK daily_bar: Eastmoney provider call failed for HK daily_bar 0700.HK; respect_env_proxy failed: AkShare provider call failed for HK daily_bar 0700.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for HK daily_bar 0700.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts
- HK 9988.HK daily_bar: Eastmoney provider call failed for HK daily_bar 9988.HK; respect_env_proxy failed: AkShare provider call failed for HK daily_bar 9988.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')); direct_no_proxy failed: AkShare provider call failed for HK daily_bar 9988.HK: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) after 2 attempts

## Next Steps

- If AkShare is not installed, install it only in a provider validation environment and rerun this script.
- Review missing fields before any strategy work.
- Cross-check A-share daily bars and valuation fields with Tushare before using them for candidate discovery.
- Treat Eastmoney daily-bar coverage as unstable until repeated probes succeed across the full sample universe.
- Keep OpenBB as optional until license and provider coverage are confirmed.
