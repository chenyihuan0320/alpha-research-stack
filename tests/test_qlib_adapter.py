from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orchestrator.evidence.models import ProviderEvidence


def _evidence(
    *,
    data_domain: str = "daily_bar",
    allowed_downstream: list[str] | None = None,
    normalized_payload: dict | None = None,
) -> ProviderEvidence:
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    return ProviderEvidence(
        evidence_id=f"ev-{data_domain}",
        run_id="run-qlib",
        market="CN",
        ticker="600519.SH",
        data_domain=data_domain,
        provider="akshare+tushare",
        provider_ticker="akshare:600519;tushare:600519.SH",
        source_updated_at=now,
        observed_at=now,
        normalized_payload=normalized_payload or {
            "compared_fields": ["open", "high", "low", "close", "volume"],
            "price_diff_pct": {"close": 0.0},
        },
        raw_field_mapping={},
        quality_flags=["adjustment_unverified:none"],
        cross_source_status="matched",
        gate_status="warn",
        allowed_downstream=allowed_downstream if allowed_downstream is not None else ["alphasift_exploratory"],
        notes="test evidence",
    )


def test_daily_bar_evidence_can_enter_qlib_feasibility() -> None:
    from orchestrator.adapters.qlib_adapter import can_send_to_qlib

    assert can_send_to_qlib(_evidence()) is True


def test_valuation_and_fundamentals_are_rejected() -> None:
    from orchestrator.adapters.qlib_adapter import can_send_to_qlib

    assert can_send_to_qlib(_evidence(data_domain="valuation", allowed_downstream=[])) is False
    assert can_send_to_qlib(_evidence(data_domain="fundamentals", allowed_downstream=[])) is False


def test_summary_only_evidence_is_partial_not_qlib_ready_panel() -> None:
    from orchestrator.adapters.qlib_adapter import evaluate_qlib_data_format_feasibility

    result = evaluate_qlib_data_format_feasibility([_evidence()])

    assert result.status == "partial"
    assert result.required_fields == ["date", "ticker", "open", "high", "low", "close", "volume"]
    assert "time_series_panel_missing" in result.warnings
    assert "build verified daily_bar panel" in result.next_action


def test_mock_full_daily_bars_are_feasible() -> None:
    from orchestrator.adapters.qlib_adapter import (
        build_qlib_format_input,
        evaluate_qlib_data_format_feasibility,
    )

    payload = {
        "daily_bars": [
            {
                "date": "2026-07-01",
                "ticker": "600519.SH",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 1000,
            },
            {
                "date": "2026-07-02",
                "ticker": "600519.SH",
                "open": 1.5,
                "high": 2.5,
                "low": 1.0,
                "close": 2.0,
                "volume": 1200,
            },
        ]
    }
    evidence = _evidence(normalized_payload=payload)

    adapter_input = build_qlib_format_input([evidence])
    result = evaluate_qlib_data_format_feasibility([evidence])

    assert adapter_input.tickers == ["600519.SH"]
    assert adapter_input.fields == ["date", "ticker", "open", "high", "low", "close", "volume"]
    assert result.status == "feasible"
    assert result.missing_fields == []


def test_no_allowed_daily_bar_rows_is_blocked() -> None:
    from orchestrator.adapters.qlib_adapter import build_qlib_format_input

    with pytest.raises(ValueError):
        build_qlib_format_input([_evidence(allowed_downstream=[])])
