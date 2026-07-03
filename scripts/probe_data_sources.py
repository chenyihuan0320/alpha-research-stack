#!/usr/bin/env python3
"""Generate a dry-run provider probe plan."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.data.provider_probe import ProviderProbeResult, build_probe_plan
from orchestrator.data.sample_universe import load_sample_universe


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
REPORT_PATH = ROOT / "outputs" / "reports" / "provider_probe_plan.md"
STATUSES = ("planned", "needs_credentials", "skipped", "unavailable")


def _markdown_table(rows: list[ProviderProbeResult]) -> str:
    lines = [
        "| provider | market | ticker | capability | status | required_fields | notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        fields = ", ".join(row.required_fields)
        notes = row.notes.replace("|", "\\|")
        lines.append(
            f"| {row.provider} | {row.market} | {row.ticker} | {row.capability} | "
            f"{row.status} | {fields} | {notes} |"
        )
    return "\n".join(lines)


def write_report(rows: list[ProviderProbeResult], report_path: Path = REPORT_PATH) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(row.status for row in rows)
    report = "\n".join(
        [
            "# Provider Probe Plan",
            "",
            "This is a dry-run plan. It does not call AkShare, Tushare, EdgarTools, OpenBB, or any external data source.",
            "",
            "## Summary",
            "",
            f"- total probe items: {len(rows)}",
            f"- planned: {counts.get('planned', 0)}",
            f"- needs_credentials: {counts.get('needs_credentials', 0)}",
            f"- skipped: {counts.get('skipped', 0)}",
            f"- unavailable: {counts.get('unavailable', 0)}",
            "",
            "## Probe Items",
            "",
            _markdown_table(rows),
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8")


def main() -> int:
    universe = load_sample_universe(UNIVERSE_PATH)
    rows = build_probe_plan(universe)
    write_report(rows)
    counts = Counter(row.status for row in rows)
    print(f"total probe items: {len(rows)}")
    for status in STATUSES:
        print(f"{status} count: {counts.get(status, 0)}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
