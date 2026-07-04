# Provider Evidence Summary

- 运行时间: 2026-07-04T11:36:34.897774+00:00
- scope: CN sample universe, domain-level provider evidence
- note: This is not candidate discovery, not a stock recommendation, not a backtest, and not trading output.

## Summary

- total_evidence: 9
- by_domain: {'daily_bar': 3, 'fundamentals': 3, 'valuation': 3}
- by_gate_status: {'block': 6, 'warn': 3}
- by_cross_source_status: {'matched': 3, 'unavailable': 6}
- allowed_downstream: {'alphasift_exploratory': 3, 'vectorbt': 3}

## Evidence Records

| ticker | domain | provider | cross_source_status | gate_status | allowed_downstream | blocked/warning reasons | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 600519.SH | daily_bar | akshare+tushare | matched | warn | alphasift_exploratory, vectorbt | adjustment_unverified:none; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume | Daily bar evidence is domain-level only; valuation/fundamentals failures are separate evidence records. |
| 600519.SH | valuation | tushare | unavailable | block | - | provider_error | Tushare daily_basic is currently rate-limited; valuation evidence remains blocked. |
| 600519.SH | fundamentals | tushare | unavailable | block | - | provider_error_or_permission_error | Current Tushare token lacks income permission; fundamentals evidence remains blocked. |
| 000001.SZ | daily_bar | akshare+tushare | matched | warn | alphasift_exploratory, vectorbt | adjustment_unverified:none; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume | Daily bar evidence is domain-level only; valuation/fundamentals failures are separate evidence records. |
| 000001.SZ | valuation | tushare | unavailable | block | - | provider_error | Tushare daily_basic is currently rate-limited; valuation evidence remains blocked. |
| 000001.SZ | fundamentals | tushare | unavailable | block | - | provider_error_or_permission_error | Current Tushare token lacks income permission; fundamentals evidence remains blocked. |
| 300750.SZ | daily_bar | akshare+tushare | matched | warn | alphasift_exploratory, vectorbt | adjustment_unverified:none; unit_unverified:amount; unit_unverified:turnover; unit_unverified:volume | Daily bar evidence is domain-level only; valuation/fundamentals failures are separate evidence records. |
| 300750.SZ | valuation | tushare | unavailable | block | - | provider_error | Tushare daily_basic is currently rate-limited; valuation evidence remains blocked. |
| 300750.SZ | fundamentals | tushare | unavailable | block | - | provider_error_or_permission_error | Current Tushare token lacks income permission; fundamentals evidence remains blocked. |

## Reuse Eligibility

- 600519.SH daily_bar: alphasift_exploratory, vectorbt
- 000001.SZ daily_bar: alphasift_exploratory, vectorbt
- 300750.SZ daily_bar: alphasift_exploratory, vectorbt

## Boundary

- Daily bar evidence passing or warning does not imply valuation or fundamentals passed.
- Valuation and fundamentals blocks do not block price-only exploratory validation.
- Downstream reuse components may only consume ProviderEvidence with explicit `allowed_downstream`.
- No AlphaSift or vectorbt execution was performed.
