"""Dry-run provider probe plan builder."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from orchestrator.data.contracts import Market


DAILY_BAR_FIELDS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "amount",
    "turnover",
    "adjustment",
]
FUNDAMENTALS_FIELDS = [
    "period_end",
    "fiscal_period",
    "report_date",
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "debt",
    "shares_outstanding",
]
VALUATION_FIELDS = [
    "date",
    "market_cap",
    "pe",
    "pb",
    "ps",
    "ev_ebitda",
    "dividend_yield",
    "fcf_yield",
]
EVENT_FIELDS = ["event_date", "event_type", "title", "summary", "url"]


@dataclass(slots=True)
class ProviderProbeResult:
    provider: str
    market: str
    ticker: str
    capability: str
    status: str
    required_fields: list[str]
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_probe_plan(universe: Iterable[dict[str, str]]) -> list[ProviderProbeResult]:
    results: list[ProviderProbeResult] = []
    for item in universe:
        market = item.get("market")
        ticker = item.get("ticker")
        if not market or not ticker:
            raise ValueError("Universe items must include market and ticker")

        if market == Market.CN.value:
            results.extend(
                [
                    ProviderProbeResult(
                        provider="AkShare",
                        market=market,
                        ticker=ticker,
                        capability="daily_bar",
                        status="planned",
                        required_fields=DAILY_BAR_FIELDS,
                        notes="Dry-run only; validate A-share ticker mapping and adjustment semantics.",
                    ),
                    ProviderProbeResult(
                        provider="AkShare",
                        market=market,
                        ticker=ticker,
                        capability="valuation_snapshot",
                        status="planned",
                        required_fields=VALUATION_FIELDS,
                        notes="Dry-run only; validate valuation coverage, units, and PE/PB definitions.",
                    ),
                    ProviderProbeResult(
                        provider="Tushare",
                        market=market,
                        ticker=ticker,
                        capability="daily_bar",
                        status="needs_credentials",
                        required_fields=DAILY_BAR_FIELDS,
                        notes="Requires Tushare token via environment variable; do not commit credentials.",
                    ),
                    ProviderProbeResult(
                        provider="Tushare",
                        market=market,
                        ticker=ticker,
                        capability="fundamentals_snapshot",
                        status="needs_credentials",
                        required_fields=FUNDAMENTALS_FIELDS,
                        notes="Requires Tushare token and permission checks for financial statement fields.",
                    ),
                ]
            )
        elif market == Market.HK.value:
            results.extend(
                [
                    ProviderProbeResult(
                        provider="AkShare",
                        market=market,
                        ticker=ticker,
                        capability="daily_bar",
                        status="planned",
                        required_fields=DAILY_BAR_FIELDS,
                        notes="Dry-run only; validate Hong Kong ticker zero-padding and HKD units.",
                    ),
                    ProviderProbeResult(
                        provider="OpenBB",
                        market=market,
                        ticker=ticker,
                        capability="daily_bar",
                        status="skipped",
                        required_fields=DAILY_BAR_FIELDS,
                        notes="Skipped until OpenBB license impact and Hong Kong provider coverage are confirmed.",
                    ),
                ]
            )
        elif market == Market.US.value:
            results.extend(
                [
                    ProviderProbeResult(
                        provider="EdgarTools",
                        market=market,
                        ticker=ticker,
                        capability="fundamentals_snapshot",
                        status="planned",
                        required_fields=FUNDAMENTALS_FIELDS,
                        notes="Dry-run only; validate ticker-to-CIK mapping and XBRL field coverage.",
                    ),
                    ProviderProbeResult(
                        provider="EdgarTools",
                        market=market,
                        ticker=ticker,
                        capability="event_record",
                        status="planned",
                        required_fields=EVENT_FIELDS,
                        notes="Dry-run only; validate 10-K/10-Q/8-K event extraction boundaries.",
                    ),
                    ProviderProbeResult(
                        provider="OpenBB",
                        market=market,
                        ticker=ticker,
                        capability="daily_bar",
                        status="skipped",
                        required_fields=DAILY_BAR_FIELDS,
                        notes="Skipped until OpenBB AGPL license impact is confirmed.",
                    ),
                    ProviderProbeResult(
                        provider="OpenBB",
                        market=market,
                        ticker=ticker,
                        capability="valuation_snapshot",
                        status="skipped",
                        required_fields=VALUATION_FIELDS,
                        notes="Skipped until OpenBB AGPL license impact and provider requirements are confirmed.",
                    ),
                ]
            )
        else:
            raise ValueError(f"Unsupported market in universe: {market}")

    return results
