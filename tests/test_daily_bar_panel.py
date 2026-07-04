from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orchestrator.evidence.models import ProviderEvidence


def _evidence(
    *,
    data_domain: str = "daily_bar",
    payload: dict | None = None,
    allowed_downstream: list[str] | None = None,
) -> ProviderEvidence:
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    return ProviderEvidence(
        evidence_id=f"ev-{data_domain}",
        run_id="run-panel",
        market="CN",
        ticker="600519.SH",
        data_domain=data_domain,
        provider="akshare+tushare",
        provider_ticker="akshare:600519;tushare:600519.SH",
        source_updated_at=now,
        observed_at=now,
        normalized_payload=payload or {"compared_fields": ["open", "high", "low", "close", "volume"]},
        raw_field_mapping={},
        quality_flags=["adjustment_unverified:none"],
        cross_source_status="matched",
        gate_status="warn",
        allowed_downstream=allowed_downstream or ["alphasift_exploratory", "vectorbt"],
        notes="test evidence",
    )


def test_summary_only_provider_evidence_cannot_be_faked_into_panel() -> None:
    from orchestrator.panels.daily_bar_panel import build_daily_bar_panel_from_provider_evidence

    result, rows = build_daily_bar_panel_from_provider_evidence([_evidence()])

    assert rows == []
    assert result.status == "blocked"
    assert "blocked_by_missing_time_series" in result.warnings


def test_mock_full_daily_bars_generate_panel_rows_with_evidence_id() -> None:
    from orchestrator.panels.daily_bar_panel import build_daily_bar_panel_from_provider_evidence

    payload = {
        "daily_bars": [
            {"date": "2026-07-01", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000, "amount": 10000},
            {"date": "2026-07-02", "open": 10.5, "high": 11.5, "low": 10.0, "close": 11.0, "volume": 2000, "amount": 22000},
        ]
    }

    result, rows = build_daily_bar_panel_from_provider_evidence([_evidence(payload=payload)])

    assert result.status == "success"
    assert result.row_count == 2
    assert rows[0].provider_evidence_id == "ev-daily_bar"
    assert rows[0].provider == "akshare+tushare"
    assert rows[0].cross_source_status == "matched"
    assert rows[0].to_dict()["ticker"] == "600519.SH"


def test_valuation_and_fundamentals_are_rejected_from_panel() -> None:
    from orchestrator.panels.daily_bar_panel import build_daily_bar_panel_from_provider_evidence

    result, rows = build_daily_bar_panel_from_provider_evidence(
        [_evidence(data_domain="valuation"), _evidence(data_domain="fundamentals")]
    )

    assert rows == []
    assert result.status == "blocked"
    assert result.missing_tickers == []


def test_validate_daily_bar_panel_requires_required_fields() -> None:
    from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, validate_daily_bar_panel

    row = DailyBarPanelRow(
        run_id="run-panel",
        market="CN",
        ticker="600519.SH",
        date="2026-07-01",
        open=10.0,
        high=11.0,
        low=9.5,
        close=10.5,
        volume=1000.0,
        amount=None,
        provider="akshare",
        provider_evidence_id="ev-1",
        cross_source_status="matched",
        quality_flags=[],
        adjustment="none",
        source_updated_at="2026-07-04T00:00:00+00:00",
    )

    assert validate_daily_bar_panel([row]) == [row]
    with pytest.raises(ValueError, match="missing required field"):
        validate_daily_bar_panel([DailyBarPanelRow(**{**row.to_dict(), "close": None})])
