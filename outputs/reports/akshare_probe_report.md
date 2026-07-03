# AkShare Provider Probe Report

- 运行时间: 2026-07-03T07:42:38.043150+00:00
- provider: akshare
- scope: CN daily_bar, CN valuation_snapshot, HK daily_bar; US skipped
- note: This report is data coverage evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.

## Summary

- success: 0
- failed: 9
- skipped: 3

## Results

| market | ticker | capability | status | rows | covered_fields | missing_fields | quality_flags | reason |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| CN | 600519.SH | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| CN | 600519.SH | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| CN | 000001.SZ | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| CN | 000001.SZ | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| CN | 300750.SZ | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| CN | 300750.SZ | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| HK | 0700.HK | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| HK | 9988.HK | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| HK | 3690.HK | daily_bar | failed | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare |
| US | AAPL | daily_bar | skipped | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |
| US | NVDA | daily_bar | skipped | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |
| US | MSFT | daily_bar | skipped | 0 | - | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | - | AkShare not primary US provider in phase 1 |

## Field Coverage Notes

- `covered_fields` means at least one returned sample row had a non-null value for that contract field.
- `missing_fields` may include fields AkShare does not provide directly, such as `ev_ebitda` or `fcf_yield`.
- `quality_flags` are adapter-level flags generated from contract/provider field mapping.

## Failure Reasons

- CN 600519.SH daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- CN 600519.SH valuation_snapshot: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- CN 000001.SZ daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- CN 000001.SZ valuation_snapshot: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- CN 300750.SZ daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- CN 300750.SZ valuation_snapshot: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- HK 0700.HK daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- HK 9988.HK daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare
- HK 3690.HK daily_bar: AkShare is not installed. Install it only when running provider probes, for example: python -m pip install akshare

## Next Steps

- If AkShare is not installed, install it only in a provider validation environment and rerun this script.
- Review missing fields before any strategy work.
- Cross-check A-share daily bars and valuation fields with Tushare before using them for candidate discovery.
- Keep OpenBB as optional until license and provider coverage are confirmed.
