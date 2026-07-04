from __future__ import annotations

from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv


def _write_panel(path) -> None:
    rows = []
    for ticker in ("600519.SH", "000001.SZ"):
        for idx, close in enumerate([100.0, 102.0, 101.0, 104.0]):
            rows.append(
                DailyBarPanelRow(
                    run_id="run-vectorbt-script",
                    market="CN",
                    ticker=ticker,
                    date=f"2026-07-0{idx + 1}",
                    open=close,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1000.0,
                    amount=10000.0,
                    provider="akshare",
                    provider_evidence_id=f"ev-{ticker}",
                    cross_source_status="unavailable",
                    quality_flags=["cross_source_panel_unavailable"],
                    adjustment="none",
                    source_updated_at="2026-07-04T00:00:00+00:00",
                )
            )
    write_daily_bar_panel_csv(rows, path)


def test_vectorbt_event_baseline_script_writes_validation_evidence_and_report(tmp_path) -> None:
    import scripts.run_vectorbt_event_baseline as script

    panel_path = tmp_path / "panel.csv"
    ledger_path = tmp_path / "validation_evidence.jsonl"
    report_path = tmp_path / "vectorbt_event_baseline.md"
    _write_panel(panel_path)

    result = script.run_vectorbt_event_baseline(
        panel_path=panel_path,
        ledger_path=ledger_path,
        report_path=report_path,
    )

    assert result["validations_written"] == 2
    assert ledger_path.exists()
    assert "fallback_event_baseline" in ledger_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    assert "| validations_written | pass | count=2 |" in report
    assert "not signal/recommendation" in report.lower()


def test_benchmark_marks_vectorbt_baseline_validated_when_validation_evidence_exists(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark
    from orchestrator.validation.ledger import append_validation
    from orchestrator.validation.models import ValidationEvidence

    ledger_path = tmp_path / "validation_evidence.jsonl"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    append_validation(
        ValidationEvidence(
            validation_id="val-1",
            run_id="run-vectorbt-script",
            market="CN",
            ticker="600519.SH",
            event_date="2026-07-03",
            validation_source="fallback_event_baseline",
            holding_period=1,
            forward_return=0.02,
            max_favorable_excursion=0.03,
            max_adverse_excursion=-0.01,
            hit_take_profit=None,
            hit_stop_loss=None,
            provider_evidence_ids=["ev-1"],
            panel_rows_used=2,
            quality_flags=[],
            raw_payload={},
            gate_status="warn",
            allowed_next_steps=["research"],
            notes="not signal",
        ),
        ledger_path,
    )

    result = benchmark.benchmark_candidate_engines(
        validation_ledger_path=ledger_path,
        report_path=report_path,
    )
    vectorbt_row = next(row for row in result["rows"] if row["engine"] == "vectorbt_event_baseline")

    assert vectorbt_row["status"] == "baseline_validated"
    assert "ValidationEvidence" in vectorbt_row["current_blocker"]
