from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orchestrator.adapters.alphasift_adapter import build_alphasift_input, can_send_to_alphasift
from orchestrator.adapters.vectorbt_adapter import build_vectorbt_input, can_send_to_vectorbt
from orchestrator.evidence.models import ProviderEvidence


def _provider_evidence(
    *,
    data_domain: str = "daily_bar",
    gate_status: str = "warn",
    allowed_downstream: list[str] | None = None,
) -> ProviderEvidence:
    now = datetime(2026, 7, 4, 10, 30, tzinfo=timezone.utc)
    return ProviderEvidence(
        evidence_id=f"ev-600519-{data_domain}",
        run_id="run-009",
        market="CN",
        ticker="600519.SH",
        data_domain=data_domain,
        provider="akshare+tushare",
        provider_ticker="akshare:600519;tushare:600519.SH",
        source_updated_at=now,
        observed_at=now,
        normalized_payload={"compared_fields": ["open", "close"], "price_diff_pct": {"close": 0.0}},
        raw_field_mapping={"akshare": {"close": "收盘"}, "tushare": {"close": "close"}},
        quality_flags=["adjustment_unverified:none"],
        cross_source_status="matched",
        gate_status=gate_status,
        allowed_downstream=(
            ["alphasift_exploratory", "vectorbt"]
            if allowed_downstream is None
            else allowed_downstream
        ),
        notes="test evidence",
    )


def test_daily_bar_provider_evidence_can_build_alphasift_input() -> None:
    evidence = _provider_evidence()

    assert can_send_to_alphasift(evidence) is True

    adapter_input = build_alphasift_input(evidence)

    assert adapter_input.run_id == "run-009"
    assert adapter_input.market == "CN"
    assert adapter_input.ticker == "600519.SH"
    assert adapter_input.candidate_date == "2026-07-04"
    assert adapter_input.quality_gate_status == "warn"
    assert adapter_input.provider_evidence["evidence_id"] == "ev-600519-daily_bar"
    assert adapter_input.provider_evidence["data_domain"] == "daily_bar"


def test_daily_bar_provider_evidence_dict_can_build_alphasift_input() -> None:
    adapter_input = build_alphasift_input(_provider_evidence().to_dict())

    assert adapter_input.provider_evidence["normalized_payload"]["price_diff_pct"]["close"] == 0.0


def test_valuation_and_fundamentals_cannot_build_alphasift_input() -> None:
    for data_domain in ("valuation", "fundamentals"):
        evidence = _provider_evidence(
            data_domain=data_domain,
            gate_status="block",
            allowed_downstream=[],
        )
        assert can_send_to_alphasift(evidence) is False
        with pytest.raises(ValueError):
            build_alphasift_input(evidence)


def test_vectorbt_build_input_requires_provider_evidence_allowed_downstream() -> None:
    evidence = _provider_evidence()

    assert can_send_to_vectorbt(evidence) is True

    adapter_input = build_vectorbt_input(evidence, event_dates=["2026-07-04"], holding_period=5)

    assert adapter_input.ticker == "600519.SH"
    assert adapter_input.market == "CN"
    assert adapter_input.quality_gate_status == "warn"
    assert adapter_input.event_dates == ["2026-07-04"]


def test_vectorbt_build_input_does_not_infer_allowed_downstream_from_gate_status() -> None:
    evidence = _provider_evidence(allowed_downstream=[])

    assert can_send_to_vectorbt(evidence) is False
    with pytest.raises(ValueError):
        build_vectorbt_input(evidence)
