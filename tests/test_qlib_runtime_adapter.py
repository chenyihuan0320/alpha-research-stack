from __future__ import annotations

import builtins

import pytest

from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv


def _write_panel(path, *, omit_field: str | None = None) -> None:
    rows = [
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
    ]
    write_daily_bar_panel_csv(rows, path)
    if omit_field is not None:
        text = path.read_text(encoding="utf-8")
        header, rest = text.split("\n", 1)
        header = ",".join(field for field in header.split(",") if field != omit_field)
        path.write_text(header + "\n" + rest, encoding="utf-8")


def test_panel_missing_returns_blocked(tmp_path) -> None:
    from orchestrator.adapters.qlib_runtime_adapter import build_qlib_runtime_read_input

    result = build_qlib_runtime_read_input(tmp_path / "missing.csv")

    assert result.status == "blocked"
    assert result.panel_readable is False
    assert "panel_missing" in result.warnings


def test_panel_schema_missing_required_field_returns_format_error(tmp_path) -> None:
    from orchestrator.adapters.qlib_runtime_adapter import build_qlib_runtime_read_input

    panel_path = tmp_path / "panel.csv"
    _write_panel(panel_path, omit_field="close")

    result = build_qlib_runtime_read_input(panel_path)

    assert result.status == "format_error"
    assert result.panel_readable is False
    assert "missing_field:close" in result.warnings


def test_valid_panel_is_readable_without_qlib(tmp_path) -> None:
    from orchestrator.adapters.qlib_runtime_adapter import validate_panel_readable_without_qlib

    panel_path = tmp_path / "panel.csv"
    _write_panel(panel_path)

    result = validate_panel_readable_without_qlib(panel_path)

    assert result.status == "success"
    assert result.panel_readable is True
    assert result.rows_read == 4
    assert result.tickers == ["000001.SZ", "600519.SH"]
    assert result.date_range == ("2026-07-01", "2026-07-02")


def test_qlib_missing_keeps_csv_validation_but_reports_dependency_missing(tmp_path, monkeypatch) -> None:
    from orchestrator.adapters.qlib_runtime_adapter import attempt_qlib_runtime_read

    panel_path = tmp_path / "panel.csv"
    _write_panel(panel_path)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qlib":
            raise ImportError("No module named qlib")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = attempt_qlib_runtime_read(panel_path)

    assert result.status == "dependency_missing"
    assert result.qlib_available is False
    assert result.panel_readable is True
    assert result.rows_read == 4


def test_qlib_runtime_success_can_be_simulated(tmp_path, monkeypatch) -> None:
    from orchestrator.adapters import qlib_runtime_adapter as adapter

    panel_path = tmp_path / "panel.csv"
    _write_panel(panel_path)
    monkeypatch.setattr(adapter, "inspect_qlib_availability", lambda: {"available": True, "version": "test", "error": None})

    result = adapter.attempt_qlib_runtime_read(panel_path)

    assert result.status == "success"
    assert result.qlib_available is True
    assert result.panel_readable is True
