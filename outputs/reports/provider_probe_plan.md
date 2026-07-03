# Provider Probe Plan

This is a dry-run plan. It does not call AkShare, Tushare, EdgarTools, OpenBB, or any external data source.

## Summary

- total probe items: 30
- planned: 15
- needs_credentials: 6
- skipped: 9
- unavailable: 0

## Probe Items

| provider | market | ticker | capability | status | required_fields | notes |
| --- | --- | --- | --- | --- | --- | --- |
| AkShare | CN | 600519.SH | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate A-share ticker mapping and adjustment semantics. |
| AkShare | CN | 600519.SH | valuation_snapshot | planned | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Dry-run only; validate valuation coverage, units, and PE/PB definitions. |
| Tushare | CN | 600519.SH | daily_bar | needs_credentials | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Requires Tushare token via environment variable; do not commit credentials. |
| Tushare | CN | 600519.SH | fundamentals_snapshot | needs_credentials | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Requires Tushare token and permission checks for financial statement fields. |
| AkShare | CN | 000001.SZ | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate A-share ticker mapping and adjustment semantics. |
| AkShare | CN | 000001.SZ | valuation_snapshot | planned | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Dry-run only; validate valuation coverage, units, and PE/PB definitions. |
| Tushare | CN | 000001.SZ | daily_bar | needs_credentials | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Requires Tushare token via environment variable; do not commit credentials. |
| Tushare | CN | 000001.SZ | fundamentals_snapshot | needs_credentials | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Requires Tushare token and permission checks for financial statement fields. |
| AkShare | CN | 300750.SZ | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate A-share ticker mapping and adjustment semantics. |
| AkShare | CN | 300750.SZ | valuation_snapshot | planned | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Dry-run only; validate valuation coverage, units, and PE/PB definitions. |
| Tushare | CN | 300750.SZ | daily_bar | needs_credentials | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Requires Tushare token via environment variable; do not commit credentials. |
| Tushare | CN | 300750.SZ | fundamentals_snapshot | needs_credentials | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Requires Tushare token and permission checks for financial statement fields. |
| AkShare | HK | 0700.HK | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate Hong Kong ticker zero-padding and HKD units. |
| OpenBB | HK | 0700.HK | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB license impact and Hong Kong provider coverage are confirmed. |
| AkShare | HK | 9988.HK | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate Hong Kong ticker zero-padding and HKD units. |
| OpenBB | HK | 9988.HK | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB license impact and Hong Kong provider coverage are confirmed. |
| AkShare | HK | 3690.HK | daily_bar | planned | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Dry-run only; validate Hong Kong ticker zero-padding and HKD units. |
| OpenBB | HK | 3690.HK | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB license impact and Hong Kong provider coverage are confirmed. |
| EdgarTools | US | AAPL | fundamentals_snapshot | planned | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Dry-run only; validate ticker-to-CIK mapping and XBRL field coverage. |
| EdgarTools | US | AAPL | event_record | planned | event_date, event_type, title, summary, url | Dry-run only; validate 10-K/10-Q/8-K event extraction boundaries. |
| OpenBB | US | AAPL | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB AGPL license impact is confirmed. |
| OpenBB | US | AAPL | valuation_snapshot | skipped | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Skipped until OpenBB AGPL license impact and provider requirements are confirmed. |
| EdgarTools | US | NVDA | fundamentals_snapshot | planned | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Dry-run only; validate ticker-to-CIK mapping and XBRL field coverage. |
| EdgarTools | US | NVDA | event_record | planned | event_date, event_type, title, summary, url | Dry-run only; validate 10-K/10-Q/8-K event extraction boundaries. |
| OpenBB | US | NVDA | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB AGPL license impact is confirmed. |
| OpenBB | US | NVDA | valuation_snapshot | skipped | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Skipped until OpenBB AGPL license impact and provider requirements are confirmed. |
| EdgarTools | US | MSFT | fundamentals_snapshot | planned | period_end, fiscal_period, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | Dry-run only; validate ticker-to-CIK mapping and XBRL field coverage. |
| EdgarTools | US | MSFT | event_record | planned | event_date, event_type, title, summary, url | Dry-run only; validate 10-K/10-Q/8-K event extraction boundaries. |
| OpenBB | US | MSFT | daily_bar | skipped | date, open, high, low, close, adj_close, volume, amount, turnover, adjustment | Skipped until OpenBB AGPL license impact is confirmed. |
| OpenBB | US | MSFT | valuation_snapshot | skipped | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | Skipped until OpenBB AGPL license impact and provider requirements are confirmed. |
