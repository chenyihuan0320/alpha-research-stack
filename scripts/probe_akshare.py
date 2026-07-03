#!/usr/bin/env python3
"""Run a minimal AkShare provider probe and write a coverage report."""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.data.providers.akshare_provider import (  # noqa: E402
    AkShareProviderError,
    fetch_cn_daily_bar_sample,
    fetch_cn_valuation_sample,
    fetch_hk_daily_bar_sample,
)
from orchestrator.data.sample_universe import load_sample_universe  # noqa: E402


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
REPORT_PATH = ROOT / "outputs" / "reports" / "akshare_probe_report.md"


@dataclass(slots=True)
class ProbeRecord:
    market: str
    ticker: str
    capability: str
    status: str
    returned_rows: int
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
        "adj_close",
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
}


def _summarize_rows(rows: list[Any], expected_fields: list[str]) -> tuple[list[str], list[str], list[str]]:
    dict_rows = [row.to_dict() for row in rows]
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


def _run_capability(
    *,
    market: str,
    ticker: str,
    capability: str,
    fetcher: Callable[[], list[Any]],
) -> ProbeRecord:
    expected = EXPECTED_FIELDS[capability]
    try:
        rows = fetcher()
    except AkShareProviderError as exc:
        return ProbeRecord(
            market=market,
            ticker=ticker,
            capability=capability,
            status="failed",
            returned_rows=0,
            covered_fields=[],
            missing_fields=expected,
            quality_flags=[],
            reason=str(exc),
        )

    covered, missing, flags = _summarize_rows(rows, expected)
    return ProbeRecord(
        market=market,
        ticker=ticker,
        capability=capability,
        status="success",
        returned_rows=len(rows),
        covered_fields=covered,
        missing_fields=missing,
        quality_flags=flags,
        reason="",
    )


def build_akshare_probe_records(universe: list[dict[str, str]]) -> list[ProbeRecord]:
    records: list[ProbeRecord] = []
    for item in universe:
        market = item["market"]
        ticker = item["ticker"]
        if market == "CN":
            records.append(
                _run_capability(
                    market=market,
                    ticker=ticker,
                    capability="daily_bar",
                    fetcher=lambda ticker=ticker: fetch_cn_daily_bar_sample(ticker),
                )
            )
            records.append(
                _run_capability(
                    market=market,
                    ticker=ticker,
                    capability="valuation_snapshot",
                    fetcher=lambda ticker=ticker: fetch_cn_valuation_sample(ticker),
                )
            )
        elif market == "HK":
            records.append(
                _run_capability(
                    market=market,
                    ticker=ticker,
                    capability="daily_bar",
                    fetcher=lambda ticker=ticker: fetch_hk_daily_bar_sample(ticker),
                )
            )
        elif market == "US":
            records.append(
                ProbeRecord(
                    market=market,
                    ticker=ticker,
                    capability="daily_bar",
                    status="skipped",
                    returned_rows=0,
                    covered_fields=[],
                    missing_fields=EXPECTED_FIELDS["daily_bar"],
                    quality_flags=[],
                    reason="AkShare not primary US provider in phase 1",
                )
            )
    return records


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def write_report(records: list[ProbeRecord], report_path: Path = REPORT_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(record.status for record in records)
    lines = [
        "# AkShare Provider Probe Report",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        "- provider: akshare",
        "- scope: CN daily_bar, CN valuation_snapshot, HK daily_bar; US skipped",
        "- note: This report is data coverage evidence only. It does not contain recommendations, scores, backtests, LLM output, or trading instructions.",
        "",
        "## Summary",
        "",
        f"- success: {counts.get('success', 0)}",
        f"- failed: {counts.get('failed', 0)}",
        f"- skipped: {counts.get('skipped', 0)}",
        "",
        "## Results",
        "",
        "| market | ticker | capability | status | rows | covered_fields | missing_fields | quality_flags | reason |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record.market} | {record.ticker} | {record.capability} | {record.status} | "
            f"{record.returned_rows} | {_format_list(record.covered_fields)} | "
            f"{_format_list(record.missing_fields)} | {_format_list(record.quality_flags)} | "
            f"{record.reason.replace('|', '\\|') or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Field Coverage Notes",
            "",
            "- `covered_fields` means at least one returned sample row had a non-null value for that contract field.",
            "- `missing_fields` may include fields AkShare does not provide directly, such as `ev_ebitda` or `fcf_yield`.",
            "- `quality_flags` are adapter-level flags generated from contract/provider field mapping.",
            "",
            "## Failure Reasons",
            "",
        ]
    )
    failures = [record for record in records if record.status == "failed"]
    if failures:
        for record in failures:
            lines.append(f"- {record.market} {record.ticker} {record.capability}: {record.reason}")
    else:
        lines.append("- No failed AkShare probe items.")

    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            "- If AkShare is not installed, install it only in a provider validation environment and rerun this script.",
            "- Review missing fields before any strategy work.",
            "- Cross-check A-share daily bars and valuation fields with Tushare before using them for candidate discovery.",
            "- Keep OpenBB as optional until license and provider coverage are confirmed.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    universe = load_sample_universe(UNIVERSE_PATH)
    records = build_akshare_probe_records(universe)
    write_report(records)
    counts = Counter(record.status for record in records)
    print(f"success count: {counts.get('success', 0)}")
    print(f"failed count: {counts.get('failed', 0)}")
    print(f"skipped count: {counts.get('skipped', 0)}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
