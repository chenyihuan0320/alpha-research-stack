# Tushare Provider Probe Report

- 运行时间: 2026-07-03T10:27:22.681582+00:00
- provider: tushare
- tushare_installed: True
- tushare_version: 1.4.29
- tushare_import_error: -
- tushare_token_present: True
- scope: CN daily_bar, valuation_snapshot, fundamentals_snapshot, trade_calendar
- note: This report is provider validation evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.

## Summary

- success: 3
- failed: 7
- needs_credentials: 0
- skipped: 0

## Results

| ticker | capability | status | rows | covered_fields | missing_fields | quality_flags | reason |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| 600519.SH | daily_bar | success | 5 | adjustment, amount, close, date, high, low, open, volume | turnover | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:volume | - |
| 600519.SH | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | provider_error | Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/小时)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |
| 600519.SH | fundamentals_snapshot | failed | 0 | - | period_end, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | provider_error | Tushare provider call failed for CN income statement 600519.SH: 抱歉，您没有接口(income)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| 000001.SZ | daily_bar | success | 5 | adjustment, amount, close, date, high, low, open, volume | turnover | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:volume | - |
| 000001.SZ | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | provider_error | Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/分钟)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |
| 000001.SZ | fundamentals_snapshot | failed | 0 | - | period_end, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | provider_error | Tushare provider call failed for CN income statement 000001.SZ: 抱歉，您没有接口(income)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| 300750.SZ | daily_bar | success | 5 | adjustment, amount, close, date, high, low, open, volume | turnover | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:volume | - |
| 300750.SZ | valuation_snapshot | failed | 0 | - | date, market_cap, pe, pb, ps, ev_ebitda, dividend_yield, fcf_yield | provider_error | Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/分钟)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |
| 300750.SZ | fundamentals_snapshot | failed | 0 | - | period_end, report_date, revenue, gross_profit, operating_income, net_income, operating_cash_flow, free_cash_flow, total_assets, total_liabilities, total_equity, debt, shares_outstanding | provider_error | Tushare provider call failed for CN income statement 300750.SZ: 抱歉，您没有接口(income)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| - | trade_calendar | failed | 0 | - | cal_date, is_open | provider_error | Tushare provider call failed for CN trade_calendar: 抱歉，您访问接口(trade_cal)频率超限(1次/小时)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |

## Notes

- `needs_credentials` is expected when `TUSHARE_TOKEN` is absent and is not a code failure.
- Tushare field units, adjustment behavior, quota/permission limits, and financial statement semantics must be verified before strategy use.
- Do not commit a real Tushare token. Pass it only through the `TUSHARE_TOKEN` environment variable.
