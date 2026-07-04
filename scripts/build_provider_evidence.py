#!/usr/bin/env python3
"""Build domain-level ProviderEvidence records from existing provider reports."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.evidence.domain_gate import evaluate_evidence_domain  # noqa: E402
from orchestrator.evidence.ledger import append_evidence, load_evidence, summarize_evidence  # noqa: E402
from orchestrator.evidence.models import ProviderEvidence  # noqa: E402
from orchestrator.data.sample_universe import load_sample_universe  # noqa: E402


UNIVERSE_PATH = ROOT / "orchestrator" / "sample_data" / "universe_sample.csv"
COMPARISON_REPORT = ROOT / "outputs" / "reports" / "akshare_tushare_comparison.md"
TUSHARE_REPORT = ROOT / "outputs" / "reports" / "tushare_probe_report.md"
LEDGER_PATH = ROOT / "outputs" / "evidence" / "provider_evidence.jsonl"
SUMMARY_PATH = ROOT / "outputs" / "reports" / "provider_evidence_summary.md"


def _parse_markdown_table(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.exists():
        return rows
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if header and len(cells) == len(header):
            rows.append(dict(zip(header, cells, strict=True)))
    return rows


def _parse_diff_list(text: str) -> dict[str, float]:
    if not text or text == "-":
        return {}
    diffs: dict[str, float] = {}
    for part in text.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            diffs[key.strip()] = float(value.strip().rstrip("%"))
        except ValueError:
            continue
    return diffs


def _split_list(text: str) -> list[str]:
    if not text or text == "-":
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _comparison_by_ticker() -> dict[str, dict[str, str]]:
    return {row["ticker"]: row for row in _parse_markdown_table(COMPARISON_REPORT) if row.get("ticker")}


def _tushare_by_ticker_capability() -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["ticker"], row["capability"]): row
        for row in _parse_markdown_table(TUSHARE_REPORT)
        if row.get("ticker") and row.get("capability")
    }


def _provider_ticker(ticker: str) -> str:
    return f"akshare:{ticker.split('.')[0]};tushare:{ticker}"


def _make_evidence(
    *,
    run_id: str,
    ticker: str,
    data_domain: str,
    provider: str,
    provider_ticker: str,
    normalized_payload: dict[str, Any],
    raw_field_mapping: dict[str, Any],
    quality_flags: list[str],
    cross_source_status: str,
    notes: str,
) -> ProviderEvidence:
    now = datetime.now(UTC)
    base = {
        "data_domain": data_domain,
        "normalized_payload": normalized_payload,
        "quality_flags": quality_flags,
        "cross_source_status": cross_source_status,
    }
    decision = evaluate_evidence_domain(base)
    return ProviderEvidence(
        evidence_id=f"{run_id}:{ticker}:{data_domain}",
        run_id=run_id,
        market="CN",
        ticker=ticker,
        data_domain=data_domain,
        provider=provider,
        provider_ticker=provider_ticker,
        source_updated_at=now,
        observed_at=now,
        normalized_payload=normalized_payload,
        raw_field_mapping=raw_field_mapping,
        quality_flags=quality_flags,
        cross_source_status=cross_source_status,
        gate_status=decision.status,
        allowed_downstream=decision.allowed_downstream,
        notes=notes,
    )


def build_provider_evidence() -> list[ProviderEvidence]:
    universe = [item for item in load_sample_universe(UNIVERSE_PATH) if item["market"] == "CN"]
    comparison = _comparison_by_ticker()
    tushare = _tushare_by_ticker_capability()
    run_id = f"provider-evidence-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    evidence_rows: list[ProviderEvidence] = []

    for item in universe:
        ticker = item["ticker"]
        comparison_row = comparison.get(ticker, {})
        daily_quality_flags = [
            flag
            for flag in _split_list(comparison_row.get("quality_flags", ""))
            if not flag.startswith("provider_error")
        ]
        price_diff = _parse_diff_list(comparison_row.get("price_diff_pct", ""))
        volume_diff = _parse_diff_list(comparison_row.get("volume_diff_pct", ""))
        amount_diff = _parse_diff_list(comparison_row.get("amount_diff_pct", ""))
        daily_cross_source_status = "matched" if all(
            abs(value) == 0 for value in [*price_diff.values(), *volume_diff.values(), *amount_diff.values()]
        ) else "mismatch"
        evidence_rows.append(
            _make_evidence(
                run_id=run_id,
                ticker=ticker,
                data_domain="daily_bar",
                provider="akshare+tushare",
                provider_ticker=_provider_ticker(ticker),
                normalized_payload={
                    "sample_summary": "AkShare vs Tushare common-date unadjusted daily_bar comparison",
                    "price_diff_pct": price_diff,
                    "volume_diff_pct": volume_diff,
                    "amount_diff_pct": amount_diff,
                    "compared_fields": _split_list(comparison_row.get("comparable_fields", "")),
                    "sample_size": "latest common trading day summary only",
                },
                raw_field_mapping={
                    "akshare": {
                        "date": "日期/date",
                        "open": "开盘/open",
                        "high": "最高/high",
                        "low": "最低/low",
                        "close": "收盘/close",
                        "volume": "成交量/volume",
                        "amount": "成交额/amount",
                    },
                    "tushare": {
                        "date": "trade_date",
                        "open": "open",
                        "high": "high",
                        "low": "low",
                        "close": "close",
                        "volume": "vol normalized hands_to_shares",
                        "amount": "amount normalized thousand_yuan_to_yuan",
                    },
                },
                quality_flags=daily_quality_flags,
                cross_source_status=daily_cross_source_status,
                notes="Daily bar evidence is domain-level only; valuation/fundamentals failures are separate evidence records.",
            )
        )

        valuation_row = tushare.get((ticker, "valuation_snapshot"), {})
        valuation_reason = valuation_row.get("reason") or comparison_row.get("reason", "")
        evidence_rows.append(
            _make_evidence(
                run_id=run_id,
                ticker=ticker,
                data_domain="valuation",
                provider="tushare",
                provider_ticker=ticker,
                normalized_payload={
                    "status": valuation_row.get("status", "unavailable"),
                    "returned_rows": valuation_row.get("rows", "0"),
                    "reason_summary": valuation_reason,
                },
                raw_field_mapping={
                    "market_cap": "total_mv",
                    "pe": "pe_ttm/pe",
                    "pb": "pb",
                    "ps": "ps_ttm",
                    "dividend_yield": "dv_ttm/dv_ratio",
                },
                quality_flags=["provider_error:valuation_snapshot"],
                cross_source_status="unavailable",
                notes="Tushare daily_basic is currently rate-limited; valuation evidence remains blocked.",
            )
        )

        fundamentals_row = tushare.get((ticker, "fundamentals_snapshot"), {})
        fundamentals_reason = fundamentals_row.get("reason", "")
        evidence_rows.append(
            _make_evidence(
                run_id=run_id,
                ticker=ticker,
                data_domain="fundamentals",
                provider="tushare",
                provider_ticker=ticker,
                normalized_payload={
                    "status": fundamentals_row.get("status", "unavailable"),
                    "returned_rows": fundamentals_row.get("rows", "0"),
                    "reason_summary": fundamentals_reason,
                },
                raw_field_mapping={
                    "income": "Tushare income",
                    "cashflow": "Tushare cashflow",
                    "balancesheet": "Tushare balancesheet",
                },
                quality_flags=["provider_error:fundamentals_snapshot", "permission_error:income"],
                cross_source_status="unavailable",
                notes="Current Tushare token lacks income permission; fundamentals evidence remains blocked.",
            )
        )

    return evidence_rows


def write_summary(path: Path = SUMMARY_PATH, ledger_path: Path = LEDGER_PATH) -> None:
    rows = load_evidence(ledger_path)
    summary = summarize_evidence(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Provider Evidence Summary",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        "- scope: CN sample universe, domain-level provider evidence",
        "- note: This is not candidate discovery, not a stock recommendation, not a backtest, and not trading output.",
        "",
        "## Summary",
        "",
        f"- total_evidence: {summary['total']}",
        f"- by_domain: {summary['by_domain']}",
        f"- by_gate_status: {summary['by_gate_status']}",
        f"- by_cross_source_status: {summary['by_cross_source_status']}",
        f"- allowed_downstream: {summary['allowed_downstream']}",
        "",
        "## Evidence Records",
        "",
        "| ticker | domain | provider | cross_source_status | gate_status | allowed_downstream | blocked/warning reasons | notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    reusable: list[str] = []
    for row in rows:
        decision = evaluate_evidence_domain(row)
        reasons = "; ".join(decision.reasons) if decision.reasons else "-"
        downstream = ", ".join(row.allowed_downstream) if row.allowed_downstream else "-"
        safe_reasons = reasons.replace("|", "\\|")
        safe_notes = (row.notes or "-").replace("|", "\\|")
        lines.append(
            f"| {row.ticker} | {row.data_domain} | {row.provider} | {row.cross_source_status} | "
            f"{row.gate_status} | {downstream} | {safe_reasons} | "
            f"{safe_notes} |"
        )
        if row.allowed_downstream:
            reusable.append(f"{row.ticker} {row.data_domain}: {downstream}")

    lines.extend(
        [
            "",
            "## Reuse Eligibility",
            "",
        ]
    )
    if reusable:
        for item in reusable:
            lines.append(f"- {item}")
    else:
        lines.append("- No evidence is currently allowed downstream.")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Daily bar evidence passing or warning does not imply valuation or fundamentals passed.",
            "- Valuation and fundamentals blocks do not block price-only exploratory validation.",
            "- Downstream reuse components may only consume ProviderEvidence with explicit `allowed_downstream`.",
            "- No AlphaSift or vectorbt execution was performed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if LEDGER_PATH.exists():
        LEDGER_PATH.unlink()
    for evidence in build_provider_evidence():
        append_evidence(evidence, LEDGER_PATH)
    write_summary()
    print(f"ledger: {LEDGER_PATH}")
    print(f"summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
