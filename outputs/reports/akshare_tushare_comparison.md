# AkShare vs Tushare Cross-Source Comparison

- 运行时间: 2026-07-03T10:27:37.116931+00:00
- scope: CN sample universe only
- tushare_token_present: True
- note: This report is data quality evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.

## Results

| ticker | status | comparable_fields | missing_fields | price_diff_pct | volume_diff_pct | amount_diff_pct | valuation_diff_pct | quality_flags | data_quality_gate | allow_candidate_discovery | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 600519.SH | partial_success | amount, close, high, low, open, volume | dividend_yield, market_cap, pb, pe, ps, turnover | close=0.0000%, high=0.0000%, low=0.0000%, open=0.0000% | volume=-0.0000% | amount=0.0000% | - | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:turnover, unit_unverified:volume, provider_error:valuation_snapshot | block | False | adjustment_unverified:none; provider_error; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume; valuation_snapshot unavailable: Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/分钟)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |
| 000001.SZ | partial_success | amount, close, high, low, open, volume | dividend_yield, market_cap, pb, pe, ps, turnover | close=0.0000%, high=0.0000%, low=0.0000%, open=0.0000% | volume=0.0000% | amount=-0.0000% | - | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:turnover, unit_unverified:volume, provider_error:valuation_snapshot | block | False | adjustment_unverified:none; provider_error; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume; valuation_snapshot unavailable: Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/分钟)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |
| 300750.SZ | partial_success | amount, close, high, low, open, volume | dividend_yield, market_cap, pb, pe, ps, turnover | close=0.0000%, high=0.0000%, low=0.0000%, open=0.0000% | volume=0.0000% | amount=-0.0000% | - | adjustment_unverified:none, unit_normalized:amount_thousand_yuan_to_yuan, unit_normalized:volume_hands_to_shares, unit_unverified:amount, unit_unverified:turnover, unit_unverified:volume, provider_error:valuation_snapshot | block | False | adjustment_unverified:none; provider_error; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume; valuation_snapshot unavailable: Tushare provider call failed for CN valuation_snapshot all-sample trade_date 20260703: 抱歉，您访问接口(daily_basic)频率超限(1次/分钟)，具体频次详情：https://tushare.pro/document/1?doc_id=108。 |

## Gate Rules

- `pending_credentials` means Tushare credentials are missing; it is not a code failure and no data is fabricated.
- Cross-source price conflicts block provider evidence from entering candidate discovery.
- Valuation/date/unit warnings must be resolved or explicitly accepted before production strategy use.
- `fcf_yield` is intentionally not compared until financial cash-flow and market-cap units are verified.
