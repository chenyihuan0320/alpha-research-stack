from __future__ import annotations

import builtins

from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, write_daily_bar_panel_csv


def _rows() -> list[DailyBarPanelRow]:
    closes = [100.0, 110.0, 105.0, 120.0]
    return [
        DailyBarPanelRow(
            run_id="run-vectorbt",
            market="CN",
            ticker="600519.SH",
            date=f"2026-07-0{idx + 1}",
            open=close,
            high=close + 2.0,
            low=close - 3.0,
            close=close,
            volume=1000.0,
            amount=10000.0,
            provider="akshare",
            provider_evidence_id="ev-1",
            cross_source_status="unavailable",
            quality_flags=["cross_source_panel_unavailable"],
            adjustment="none",
            source_updated_at="2026-07-04T00:00:00+00:00",
        )
        for idx, close in enumerate(closes)
    ]


def test_fallback_event_validation_calculates_forward_return_mfe_mae() -> None:
    from orchestrator.adapters.vectorbt_event_adapter import validate_event_with_fallback

    result = validate_event_with_fallback(_rows(), event_date="2026-07-02", holding_period=2)

    assert result.status == "success"
    assert round(result.forward_return or 0, 6) == round((120.0 / 110.0) - 1.0, 6)
    assert round(result.max_favorable_excursion or 0, 6) == round((122.0 / 110.0) - 1.0, 6)
    assert round(result.max_adverse_excursion or 0, 6) == round((102.0 / 110.0) - 1.0, 6)
    assert result.rows_used == 3


def test_fallback_event_validation_reports_insufficient_history() -> None:
    from orchestrator.adapters.vectorbt_event_adapter import validate_event_with_fallback

    result = validate_event_with_fallback(_rows(), event_date="2026-07-04", holding_period=2)

    assert result.status == "insufficient_history"
    assert result.forward_return is None
    assert "insufficient_history" in result.warnings


def test_build_event_inputs_from_panel_selects_last_verifiable_event_date(tmp_path) -> None:
    from orchestrator.adapters.vectorbt_event_adapter import build_event_inputs_from_panel

    panel_path = tmp_path / "panel.csv"
    write_daily_bar_panel_csv(_rows(), panel_path)

    inputs = build_event_inputs_from_panel(panel_path, holding_period=1)

    assert len(inputs) == 1
    assert inputs[0].event_date == "2026-07-03"
    assert inputs[0].provider_evidence_id == "ev-1"


def test_vectorbt_missing_uses_fallback(tmp_path, monkeypatch) -> None:
    from orchestrator.adapters.vectorbt_event_adapter import attempt_vectorbt_event_validation, build_event_inputs_from_panel

    panel_path = tmp_path / "panel.csv"
    write_daily_bar_panel_csv(_rows(), panel_path)
    event_input = build_event_inputs_from_panel(panel_path, holding_period=1)[0]
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "vectorbt":
            raise ImportError("No module named vectorbt")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = attempt_vectorbt_event_validation(event_input)

    assert result.status == "success"
    assert result.raw_payload["validation_source"] == "fallback_event_baseline"
    assert "vectorbt_dependency_missing" in result.warnings
