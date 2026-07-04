from __future__ import annotations

from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv


def _write_panel(path) -> None:
    write_daily_bar_panel_csv(
        [
            DailyBarPanelRow(
                run_id="run-qlib-runtime",
                market="CN",
                ticker=ticker,
                date=day,
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000.0,
                amount=10000.0,
                provider="akshare",
                provider_evidence_id=f"ev-{ticker}",
                cross_source_status="unavailable",
                quality_flags=["cross_source_panel_unavailable"],
                adjustment="none",
                source_updated_at="2026-07-04T00:00:00+00:00",
            )
            for ticker in ("600519.SH", "000001.SZ")
            for day in ("2026-07-01", "2026-07-02")
        ],
        path,
    )


def test_runtime_read_script_reports_dependency_missing_without_failing(tmp_path, monkeypatch) -> None:
    import scripts.validate_qlib_runtime_read as script

    panel_path = tmp_path / "panel.csv"
    report_path = tmp_path / "qlib_runtime_read_validation.md"
    _write_panel(panel_path)
    monkeypatch.setattr(
        script,
        "attempt_qlib_runtime_read",
        lambda panel_path: script.QlibRuntimeReadResult(
            status="dependency_missing",
            qlib_available=False,
            panel_readable=True,
            rows_read=4,
            tickers=["000001.SZ", "600519.SH"],
            date_range=("2026-07-01", "2026-07-02"),
            warnings=["qlib_dependency_missing"],
            next_action="install qlib only if runtime validation is approved.",
        ),
    )

    result = script.validate_qlib_runtime_read(panel_path=panel_path, report_path=report_path)
    report = report_path.read_text(encoding="utf-8")

    assert result["qlib_runtime_read"] == "dependency_missing"
    assert result["panel_readable"] is True
    assert "| qlib_runtime_read | dependency_missing |" in report
    assert "Does not train models" in report


def test_benchmark_uses_runtime_read_report_for_dependency_missing_status(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark

    evidence_path = tmp_path / "provider_evidence.jsonl"
    panel_path = tmp_path / "panel.csv"
    benchmark_report = tmp_path / "candidate_engine_benchmark.md"
    runtime_report = tmp_path / "qlib_runtime_read_validation.md"
    _write_panel(panel_path)
    runtime_report.write_text(
        "\n".join(
            [
                "# Qlib Runtime Read Validation",
                "",
                "| item | status | detail |",
                "|---|---|---|",
                "| panel_schema | pass | required fields present |",
                "| qlib_runtime_read | dependency_missing | qlib missing; panel readable |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = benchmark.benchmark_candidate_engines(
        evidence_path=evidence_path,
        panel_path=panel_path,
        qlib_runtime_report_path=runtime_report,
        report_path=benchmark_report,
    )
    qlib_row = next(row for row in result["rows"] if row["engine"] == "qlib")

    assert qlib_row["status"] == "dependency_missing_panel_ready"
    assert "Qlib dependency missing" in qlib_row["current_blocker"]


def test_benchmark_uses_runtime_success_status(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark

    panel_path = tmp_path / "panel.csv"
    runtime_report = tmp_path / "qlib_runtime_read_validation.md"
    benchmark_report = tmp_path / "candidate_engine_benchmark.md"
    _write_panel(panel_path)
    runtime_report.write_text(
        "\n".join(
            [
                "# Qlib Runtime Read Validation",
                "",
                "| item | status | detail |",
                "|---|---|---|",
                "| qlib_runtime_read | success | qlib import and panel read succeeded |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = benchmark.benchmark_candidate_engines(
        panel_path=panel_path,
        qlib_runtime_report_path=runtime_report,
        report_path=benchmark_report,
    )
    qlib_row = next(row for row in result["rows"] if row["engine"] == "qlib")

    assert qlib_row["status"] == "ready_for_minimal_experiment_design"
    assert "read validation succeeded" in qlib_row["current_blocker"]
