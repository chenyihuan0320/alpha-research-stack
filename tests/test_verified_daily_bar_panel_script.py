from __future__ import annotations

import csv
from datetime import datetime, timezone

from orchestrator.evidence.ledger import append_evidence
from orchestrator.evidence.models import ProviderEvidence


def _append_daily_bar_evidence(path, ticker: str, bars: list[dict]) -> None:
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id=f"ev-{ticker}",
            run_id="run-panel-script",
            market="CN",
            ticker=ticker,
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker=f"akshare:{ticker};tushare:{ticker}",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"daily_bars": bars},
            raw_field_mapping={},
            quality_flags=["adjustment_unverified:none"],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["alphasift_exploratory", "vectorbt"],
            notes="test panel evidence",
        ),
        path,
    )


def test_verified_daily_bar_panel_script_writes_panel_and_report(tmp_path) -> None:
    import scripts.build_verified_daily_bar_panel as panel_script

    evidence_path = tmp_path / "provider_evidence.jsonl"
    output_path = tmp_path / "cn_daily_bar_panel.csv"
    report_path = tmp_path / "verified_daily_bar_panel.md"
    bars = [
        {"date": "2026-07-01", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000, "amount": 10000},
        {"date": "2026-07-02", "open": 10.5, "high": 11.5, "low": 10.0, "close": 11.0, "volume": 2000, "amount": 22000},
    ]
    _append_daily_bar_evidence(evidence_path, "600519.SH", bars)
    _append_daily_bar_evidence(evidence_path, "000001.SZ", bars)

    result = panel_script.build_verified_daily_bar_panel(
        evidence_path=evidence_path,
        output_path=output_path,
        report_path=report_path,
    )

    assert result["panel_build_status"] == "success"
    assert output_path.exists()
    rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
    assert len(rows) == 4
    assert rows[0]["provider_evidence_id"].startswith("ev-")
    report = report_path.read_text(encoding="utf-8")
    assert "| qlib_minimum_fields | pass |" in report
    assert "not a recommendation" in report.lower()


def test_qlib_feasibility_uses_existing_panel(tmp_path) -> None:
    import scripts.check_qlib_data_feasibility as qlib_script
    from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv

    evidence_path = tmp_path / "provider_evidence.jsonl"
    panel_path = tmp_path / "cn_daily_bar_panel.csv"
    report_path = tmp_path / "qlib_data_feasibility.md"
    rows = []
    for ticker in ("600519.SH", "000001.SZ"):
        for day in ("2026-07-01", "2026-07-02"):
            rows.append(
                DailyBarPanelRow(
                    run_id="run-panel-script",
                    market="CN",
                    ticker=ticker,
                    date=day,
                    open=10.0,
                    high=11.0,
                    low=9.5,
                    close=10.5,
                    volume=1000.0,
                    amount=10000.0,
                    provider="akshare+tushare",
                    provider_evidence_id=f"ev-{ticker}",
                    cross_source_status="matched",
                    quality_flags=[],
                    adjustment="none",
                    source_updated_at="2026-07-04T00:00:00+00:00",
                )
            )
    write_daily_bar_panel_csv(rows, panel_path)

    result = qlib_script.check_qlib_data_feasibility(
        evidence_path=evidence_path,
        panel_path=panel_path,
        report_path=report_path,
    )

    assert result["qlib_runtime_ready"] == "yes"
    assert result["feasibility_status"] == "feasible"
    assert "| time_series_panel | pass | complete daily_bar panel present" in report_path.read_text(encoding="utf-8")


def test_candidate_engine_benchmark_uses_panel_for_qlib_status(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark
    from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv

    evidence_path = tmp_path / "provider_evidence.jsonl"
    panel_path = tmp_path / "cn_daily_bar_panel.csv"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-1",
            run_id="run-benchmark",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"compared_fields": ["open", "high", "low", "close", "volume"]},
            raw_field_mapping={},
            quality_flags=[],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["vectorbt"],
            notes="summary only",
        ),
        evidence_path,
    )
    write_daily_bar_panel_csv(
        [
            DailyBarPanelRow(
                run_id="run-benchmark",
                market="CN",
                ticker=ticker,
                date=day,
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000.0,
                amount=10000.0,
                provider="akshare+tushare",
                provider_evidence_id=f"ev-{ticker}",
                cross_source_status="matched",
                quality_flags=[],
                adjustment="none",
                source_updated_at="2026-07-04T00:00:00+00:00",
            )
            for ticker in ("600519.SH", "000001.SZ")
            for day in ("2026-07-01", "2026-07-02")
        ],
        panel_path,
    )

    result = benchmark.benchmark_candidate_engines(
        evidence_path=evidence_path,
        panel_path=panel_path,
        report_path=report_path,
    )
    qlib_row = next(row for row in result["rows"] if row["engine"] == "qlib")

    assert qlib_row["status"] == "ready_for_runtime_validation"
    assert "runtime still not executed" in qlib_row["current_blocker"]
