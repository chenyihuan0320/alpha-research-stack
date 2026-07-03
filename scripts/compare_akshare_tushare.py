#!/usr/bin/env python3
"""Compare AkShare and Tushare A-share samples for data validation."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.data.providers.akshare_provider import (  # noqa: E402
    AkShareProviderError,
    fetch_cn_daily_bar_sample as fetch_akshare_daily,
    fetch_cn_valuation_sample as fetch_akshare_valuation,
)
from orchestrator.data.providers.tushare_provider import (  # noqa: E402
    TushareProviderError,
    fetch_cn_daily_bar_sample as fetch_tushare_daily,
    fetch_cn_valuation_sample as fetch_tushare_valuation,
    get_tushare_token,
)
from orchestrator.data.quality_gate import evaluate_cross_source_comparison  # noqa: E402
from orchestrator.data.sample_universe import load_sample_universe  # noqa: E402


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
REPORT_PATH = ROOT / "outputs" / "reports" / "akshare_tushare_comparison.md"

DAILY_FIELDS = ["open", "high", "low", "close", "volume", "amount", "turnover"]
VALUATION_FIELDS = ["market_cap", "pe", "pb", "ps", "dividend_yield"]


@dataclass(slots=True)
class ComparisonRecord:
    ticker: str
    status: str
    comparable_fields: list[str]
    missing_fields: list[str]
    price_diff_pct: dict[str, float]
    volume_diff_pct: dict[str, float]
    amount_diff_pct: dict[str, float]
    valuation_diff_pct: dict[str, float]
    quality_flags: list[str]
    gate_status: str
    allow_candidate_discovery: bool
    reason: str


def _dict_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [row.to_dict() if hasattr(row, "to_dict") else dict(row) for row in rows]


def _latest_by_date(rows: list[Any]) -> dict[str, Any] | None:
    dict_rows = _dict_rows(rows)
    if not dict_rows:
        return None
    return sorted(dict_rows, key=lambda item: str(item.get("date", "")))[-1]


def _latest_common_by_date(
    left_rows: list[Any], right_rows: list[Any]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    left_by_date = {str(row.get("date")): row for row in _dict_rows(left_rows) if row.get("date")}
    right_by_date = {str(row.get("date")): row for row in _dict_rows(right_rows) if row.get("date")}
    common_dates = sorted(set(left_by_date) & set(right_by_date))
    if not common_dates:
        return None
    target = common_dates[-1]
    return left_by_date[target], right_by_date[target]

def _pct_diff(left: Any, right: Any) -> float | None:
    try:
        left_float = float(left)
        right_float = float(right)
    except (TypeError, ValueError):
        return None
    denominator = abs(right_float)
    if denominator == 0:
        return None
    return round(((left_float - right_float) / denominator) * 100.0, 4)


def _compare_fields(
    akshare_row: dict[str, Any], tushare_row: dict[str, Any], fields: list[str]
) -> tuple[list[str], list[str], dict[str, float]]:
    comparable: list[str] = []
    missing: list[str] = []
    diffs: dict[str, float] = {}
    for field in fields:
        left = akshare_row.get(field)
        right = tushare_row.get(field)
        if left is None or right is None:
            missing.append(field)
            continue
        comparable.append(field)
        diff = _pct_diff(left, right)
        if diff is not None:
            diffs[field] = diff
    return comparable, missing, diffs


def _pending_record(ticker: str) -> ComparisonRecord:
    decision = evaluate_cross_source_comparison({"status": "pending_credentials"})
    return ComparisonRecord(
        ticker=ticker,
        status="pending_credentials",
        comparable_fields=[],
        missing_fields=DAILY_FIELDS + VALUATION_FIELDS,
        price_diff_pct={},
        volume_diff_pct={},
        amount_diff_pct={},
        valuation_diff_pct={},
        quality_flags=["pending_credentials:TUSHARE_TOKEN"],
        gate_status=decision.status,
        allow_candidate_discovery=False,
        reason="TUSHARE_TOKEN is not set.",
    )


def build_comparison_records(universe: list[dict[str, str]]) -> list[ComparisonRecord]:
    cn_items = [item for item in universe if item["market"] == "CN"]
    if get_tushare_token() is None:
        return [_pending_record(item["ticker"]) for item in cn_items]

    records: list[ComparisonRecord] = []
    for item in cn_items:
        ticker = item["ticker"]
        try:
            daily_pair = _latest_common_by_date(fetch_akshare_daily(ticker, adjust="none"), fetch_tushare_daily(ticker))
            if not daily_pair:
                raise TushareProviderError("One or more providers returned no common-date daily_bar rows.")
            ak_daily, ts_daily = daily_pair
            daily_comparable, daily_missing, daily_diffs = _compare_fields(ak_daily, ts_daily, DAILY_FIELDS)
            val_comparable: list[str] = []
            val_missing = list(VALUATION_FIELDS)
            val_diffs: dict[str, float] = {}
            flags = sorted(
                {
                    *ak_daily.get("quality_flags", []),
                    *ts_daily.get("quality_flags", []),
                }
            )
            valuation_reason = ""
            try:
                ak_val = _latest_by_date(fetch_akshare_valuation(ticker))
                ts_val = _latest_by_date(fetch_tushare_valuation(ticker))
                if ak_val and ts_val:
                    val_comparable, val_missing, val_diffs = _compare_fields(ak_val, ts_val, VALUATION_FIELDS)
                    flags = sorted(
                        {
                            *flags,
                            *ak_val.get("quality_flags", []),
                            *ts_val.get("quality_flags", []),
                        }
                    )
                else:
                    valuation_reason = "valuation_snapshot returned no comparable rows"
                    flags.append("provider_error:valuation_snapshot")
            except (AkShareProviderError, TushareProviderError) as exc:
                valuation_reason = f"valuation_snapshot unavailable: {exc}"
                flags.append("provider_error:valuation_snapshot")
            payload = {
                "quality_flags": flags,
                "price_diff_pct": {key: value for key, value in daily_diffs.items() if key in {"open", "high", "low", "close"}},
                "volume_diff_pct": {key: value for key, value in daily_diffs.items() if key == "volume"},
                "amount_diff_pct": {key: value for key, value in daily_diffs.items() if key == "amount"},
                "valuation_diff_pct": val_diffs,
            }
            decision = evaluate_cross_source_comparison(payload)
            reasons = list(decision.reasons)
            if valuation_reason:
                reasons.append(valuation_reason)
            records.append(
                ComparisonRecord(
                    ticker=ticker,
                    status="success" if not valuation_reason else "partial_success",
                    comparable_fields=sorted(set(daily_comparable + val_comparable)),
                    missing_fields=sorted(set(daily_missing + val_missing)),
                    price_diff_pct=payload["price_diff_pct"],
                    volume_diff_pct=payload["volume_diff_pct"],
                    amount_diff_pct=payload["amount_diff_pct"],
                    valuation_diff_pct=payload["valuation_diff_pct"],
                    quality_flags=flags,
                    gate_status=decision.status,
                    allow_candidate_discovery=decision.status == "pass",
                    reason="; ".join(sorted(set(reasons))),
                )
            )
        except (AkShareProviderError, TushareProviderError) as exc:
            decision = evaluate_cross_source_comparison({"quality_flags": ["provider_error"]})
            records.append(
                ComparisonRecord(
                    ticker=ticker,
                    status="failed",
                    comparable_fields=[],
                    missing_fields=DAILY_FIELDS + VALUATION_FIELDS,
                    price_diff_pct={},
                    volume_diff_pct={},
                    amount_diff_pct={},
                    valuation_diff_pct={},
                    quality_flags=["provider_error"],
                    gate_status=decision.status,
                    allow_candidate_discovery=False,
                    reason=str(exc),
                )
            )
    return records


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _format_dict(values: dict[str, float]) -> str:
    return ", ".join(f"{key}={value:.4f}%" for key, value in sorted(values.items())) if values else "-"


def write_report(records: list[ComparisonRecord], report_path: Path = REPORT_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AkShare vs Tushare Cross-Source Comparison",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        "- scope: CN sample universe only",
        f"- tushare_token_present: {get_tushare_token() is not None}",
        "- note: This report is data quality evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.",
        "",
        "## Results",
        "",
        "| ticker | status | comparable_fields | missing_fields | price_diff_pct | volume_diff_pct | amount_diff_pct | valuation_diff_pct | quality_flags | data_quality_gate | allow_candidate_discovery | reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        reason = record.reason.replace("|", "\\|") or "-"
        lines.append(
            f"| {record.ticker} | {record.status} | {_format_list(record.comparable_fields)} | "
            f"{_format_list(record.missing_fields)} | {_format_dict(record.price_diff_pct)} | "
            f"{_format_dict(record.volume_diff_pct)} | {_format_dict(record.amount_diff_pct)} | "
            f"{_format_dict(record.valuation_diff_pct)} | {_format_list(record.quality_flags)} | "
            f"{record.gate_status} | {record.allow_candidate_discovery} | {reason} |"
        )
    lines.extend(
        [
            "",
            "## Gate Rules",
            "",
            "- `pending_credentials` means Tushare credentials are missing; it is not a code failure and no data is fabricated.",
            "- Cross-source price conflicts block provider evidence from entering candidate discovery.",
            "- Valuation/date/unit warnings must be resolved or explicitly accepted before production strategy use.",
            "- `fcf_yield` is intentionally not compared until financial cash-flow and market-cap units are verified.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    universe = load_sample_universe(UNIVERSE_PATH)
    records = build_comparison_records(universe)
    write_report(records)
    print(f"comparison rows: {len(records)}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
