#!/usr/bin/env python3
"""Run a minimal AkShare provider probe and write a coverage report."""

from __future__ import annotations

import sys
import time
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
    get_akshare_import_status,
    get_eastmoney_call_history,
    get_eastmoney_proxy_bypass_status,
    reset_eastmoney_call_history,
)
from orchestrator.data.contracts import QualityFlag  # noqa: E402
from orchestrator.data.sample_universe import load_sample_universe  # noqa: E402


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
REPORT_PATH = ROOT / "outputs" / "reports" / "akshare_probe_report.md"
PROBE_ATTEMPTS = 2


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
    field_coverage_pct: float
    sample_keys: list[str]
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


def _summarize_rows(
    rows: list[Any], expected_fields: list[str]
) -> tuple[list[str], list[str], list[str], list[str]]:
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
    sample_keys = list(dict_rows[0].keys()) if dict_rows else []
    return covered, missing, flags, sample_keys


def _run_capability(
    *,
    market: str,
    ticker: str,
    capability: str,
    fetcher: Callable[[], list[Any]],
) -> ProbeRecord:
    expected = EXPECTED_FIELDS[capability]
    last_error: AkShareProviderError | None = None
    rows: list[Any] = []
    for attempt in range(1, PROBE_ATTEMPTS + 1):
        try:
            rows = fetcher()
            last_error = None
            break
        except AkShareProviderError as exc:
            last_error = exc
            if attempt < PROBE_ATTEMPTS:
                time.sleep(1)
    if last_error is not None:
        return ProbeRecord(
            market=market,
            ticker=ticker,
            capability=capability,
            status="failed",
            returned_rows=0,
            covered_fields=[],
            missing_fields=expected,
            quality_flags=[QualityFlag.PROVIDER_ERROR.value],
            field_coverage_pct=0.0,
            sample_keys=[],
            reason=f"{last_error} after {PROBE_ATTEMPTS} attempts",
        )

    covered, missing, flags, sample_keys = _summarize_rows(rows, expected)
    coverage_pct = round((len(covered) / len(expected)) * 100, 1) if expected else 100.0
    return ProbeRecord(
        market=market,
        ticker=ticker,
        capability=capability,
        status="success",
        returned_rows=len(rows),
        covered_fields=covered,
        missing_fields=missing,
        quality_flags=flags,
        field_coverage_pct=coverage_pct,
        sample_keys=sample_keys,
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
                    field_coverage_pct=0.0,
                    sample_keys=[],
                    reason="AkShare not primary US provider in phase 1",
                )
            )
    return records


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _summarize_eastmoney_history(history: list[dict[str, str]]) -> tuple[str, str]:
    if not history:
        return "none", "no Eastmoney daily_bar calls recorded"
    effective_modes = sorted(
        {
            f"{item['attempted_mode']}/{item.get('transport', 'unknown')}"
            for item in history
            if item.get("status") == "success"
        }
    )
    effective = ", ".join(effective_modes) if effective_modes else "none"
    parts: list[str] = []
    for mode in ("respect_env_proxy", "direct_no_proxy"):
        transports = sorted({item.get("transport", "unknown") for item in history if item.get("attempted_mode") == mode})
        for transport in transports:
            successes = sum(
                1
                for item in history
                if item.get("attempted_mode") == mode
                and item.get("transport", "unknown") == transport
                and item.get("status") == "success"
            )
            failures = sum(
                1
                for item in history
                if item.get("attempted_mode") == mode
                and item.get("transport", "unknown") == transport
                and item.get("status") == "failed"
            )
            if successes or failures:
                parts.append(f"{mode}/{transport}: success={successes}, failed={failures}")
    return effective, "; ".join(parts) if parts else "no Eastmoney daily_bar calls recorded"


def write_report(records: list[ProbeRecord], report_path: Path = REPORT_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(record.status for record in records)
    import_status = get_akshare_import_status()
    proxy_bypass_status = get_eastmoney_proxy_bypass_status()
    call_history = get_eastmoney_call_history()
    effective_proxy_mode, retry_mode_summary = _summarize_eastmoney_history(call_history)
    lines = [
        "# AkShare Provider Probe Report",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        "- provider: akshare",
        f"- akshare_installed: {import_status['installed']}",
        f"- akshare_version: {import_status['version'] or '-'}",
        f"- akshare_import_error: {import_status['error'] or '-'}",
        f"- configured_proxy_mode: {proxy_bypass_status['configured_proxy_mode']}",
        f"- daily_source_mode: {proxy_bypass_status.get('daily_source_mode', '-')}",
        f"- effective_proxy_mode: {effective_proxy_mode}",
        f"- daily_bar_retry_mode_summary: {retry_mode_summary}",
        f"- eastmoney_proxy_bypass: {proxy_bypass_status['enabled']}",
        f"- eastmoney_proxy_mode: {proxy_bypass_status['mode']}",
        f"- eastmoney_no_proxy: {proxy_bypass_status['no_proxy']}",
        f"- proxy_env_vars_present_outside_eastmoney_call: {proxy_bypass_status['proxy_env_vars_present']}",
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
        "| market | ticker | capability | status | rows | coverage_pct | sample_keys | covered_fields | missing_fields | quality_flags | reason |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record.market} | {record.ticker} | {record.capability} | {record.status} | "
            f"{record.returned_rows} | {record.field_coverage_pct:.1f}% | "
            f"{_format_list(record.sample_keys[:20])} | {_format_list(record.covered_fields)} | "
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
            "- `sample_keys` shows the first returned normalized sample row's key names, capped to 20 keys; it does not include full market data.",
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
            "- Treat Eastmoney daily-bar coverage as unstable until repeated probes succeed across the full sample universe.",
            "- Keep OpenBB as optional until license and provider coverage are confirmed.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    universe = load_sample_universe(UNIVERSE_PATH)
    reset_eastmoney_call_history()
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
