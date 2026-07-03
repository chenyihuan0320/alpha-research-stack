#!/usr/bin/env python3
"""Run a minimal Tushare provider probe and write a coverage report."""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.data.contracts import QualityFlag  # noqa: E402
from orchestrator.data.providers.tushare_provider import (  # noqa: E402
    TushareProviderError,
    fetch_cn_daily_bar_sample,
    fetch_cn_financial_snapshot_sample,
    fetch_cn_valuation_sample,
    fetch_trade_calendar_sample,
    get_tushare_import_status,
    get_tushare_token,
)
from orchestrator.data.sample_universe import load_sample_universe  # noqa: E402


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
REPORT_PATH = ROOT / "outputs" / "reports" / "tushare_probe_report.md"


@dataclass(slots=True)
class ProbeRecord:
    ticker: str
    capability: str
    status: str
    rows: int
    covered_fields: list[str]
    missing_fields: list[str]
    quality_flags: list[str]
    reason: str


EXPECTED_FIELDS = {
    "daily_bar": [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "turnover",
        "adjustment",
    ],
    "valuation_snapshot": [
        "date",
        "market_cap",
        "pe",
        "pb",
        "ps",
        "ev_ebitda",
        "dividend_yield",
        "fcf_yield",
    ],
    "fundamentals_snapshot": [
        "period_end",
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
    ],
    "trade_calendar": ["cal_date", "is_open"],
}


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _summarize_rows(rows: list[Any], expected_fields: list[str]) -> tuple[list[str], list[str], list[str]]:
    dict_rows = [row.to_dict() if hasattr(row, "to_dict") else dict(row) for row in rows]
    covered = sorted(
        field
        for field in expected_fields
        if any(item.get(field) is not None for item in dict_rows)
    )
    missing = sorted(field for field in expected_fields if field not in covered)
    flags = sorted(
        {
            flag
            for item in dict_rows
            for flag in item.get("quality_flags", [])
        }
    )
    return covered, missing, flags


def _needs_credentials_record(ticker: str, capability: str) -> ProbeRecord:
    return ProbeRecord(
        ticker=ticker,
        capability=capability,
        status="needs_credentials",
        rows=0,
        covered_fields=[],
        missing_fields=EXPECTED_FIELDS[capability],
        quality_flags=["needs_credentials:TUSHARE_TOKEN"],
        reason="TUSHARE_TOKEN is not set.",
    )


def _run_capability(
    *, ticker: str, capability: str, fetcher: Callable[[], list[Any]]
) -> ProbeRecord:
    expected = EXPECTED_FIELDS[capability]
    try:
        rows = fetcher()
    except TushareProviderError as exc:
        reason = str(exc)
        status = "needs_credentials" if "needs_credentials" in reason else "failed"
        flags = ["needs_credentials:TUSHARE_TOKEN"] if status == "needs_credentials" else [QualityFlag.PROVIDER_ERROR.value]
        return ProbeRecord(
            ticker=ticker,
            capability=capability,
            status=status,
            rows=0,
            covered_fields=[],
            missing_fields=expected,
            quality_flags=flags,
            reason=reason,
        )
    covered, missing, flags = _summarize_rows(rows, expected)
    return ProbeRecord(
        ticker=ticker,
        capability=capability,
        status="success",
        rows=len(rows),
        covered_fields=covered,
        missing_fields=missing,
        quality_flags=flags,
        reason="",
    )


def build_tushare_probe_records(universe: list[dict[str, str]]) -> list[ProbeRecord]:
    cn_items = [item for item in universe if item["market"] == "CN"]
    records: list[ProbeRecord] = []
    token_present = get_tushare_token() is not None
    capabilities = ("daily_bar", "valuation_snapshot", "fundamentals_snapshot")
    if not token_present:
        for item in cn_items:
            for capability in capabilities:
                records.append(_needs_credentials_record(item["ticker"], capability))
        records.append(_needs_credentials_record("-", "trade_calendar"))
        return records

    for item in cn_items:
        ticker = item["ticker"]
        records.append(
            _run_capability(
                ticker=ticker,
                capability="daily_bar",
                fetcher=lambda ticker=ticker: fetch_cn_daily_bar_sample(ticker),
            )
        )
        records.append(
            _run_capability(
                ticker=ticker,
                capability="valuation_snapshot",
                fetcher=lambda ticker=ticker: fetch_cn_valuation_sample(ticker),
            )
        )
        records.append(
            _run_capability(
                ticker=ticker,
                capability="fundamentals_snapshot",
                fetcher=lambda ticker=ticker: fetch_cn_financial_snapshot_sample(ticker),
            )
        )
    records.append(
        _run_capability(
            ticker="-",
            capability="trade_calendar",
            fetcher=fetch_trade_calendar_sample,
        )
    )
    return records


def write_report(records: list[ProbeRecord], report_path: Path = REPORT_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(record.status for record in records)
    import_status = get_tushare_import_status()
    token_present = get_tushare_token() is not None
    lines = [
        "# Tushare Provider Probe Report",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        "- provider: tushare",
        f"- tushare_installed: {import_status['installed']}",
        f"- tushare_version: {import_status['version'] or '-'}",
        f"- tushare_import_error: {import_status['error'] or '-'}",
        f"- tushare_token_present: {token_present}",
        "- scope: CN daily_bar, valuation_snapshot, fundamentals_snapshot, trade_calendar",
        "- note: This report is provider validation evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.",
        "",
        "## Summary",
        "",
        f"- success: {counts.get('success', 0)}",
        f"- failed: {counts.get('failed', 0)}",
        f"- needs_credentials: {counts.get('needs_credentials', 0)}",
        f"- skipped: {counts.get('skipped', 0)}",
        "",
        "## Results",
        "",
        "| ticker | capability | status | rows | covered_fields | missing_fields | quality_flags | reason |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for record in records:
        reason = record.reason.replace("|", "\\|") or "-"
        lines.append(
            f"| {record.ticker} | {record.capability} | {record.status} | {record.rows} | "
            f"{_format_list(record.covered_fields)} | {_format_list(record.missing_fields)} | "
            f"{_format_list(record.quality_flags)} | {reason} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `needs_credentials` is expected when `TUSHARE_TOKEN` is absent and is not a code failure.",
            "- Tushare field units, adjustment behavior, quota/permission limits, and financial statement semantics must be verified before strategy use.",
            "- Do not commit a real Tushare token. Pass it only through the `TUSHARE_TOKEN` environment variable.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    universe = load_sample_universe(UNIVERSE_PATH)
    records = build_tushare_probe_records(universe)
    write_report(records)
    counts = Counter(record.status for record in records)
    print(f"success count: {counts.get('success', 0)}")
    print(f"failed count: {counts.get('failed', 0)}")
    print(f"needs_credentials count: {counts.get('needs_credentials', 0)}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
