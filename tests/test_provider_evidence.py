from datetime import UTC, datetime

from orchestrator.adapters.alphasift_adapter import can_send_to_alphasift
from orchestrator.adapters.vectorbt_adapter import can_send_to_vectorbt
from orchestrator.evidence.models import ProviderEvidence


def test_provider_evidence_to_dict_normalizes_datetimes() -> None:
    now = datetime(2026, 7, 4, tzinfo=UTC)
    evidence = ProviderEvidence(
        evidence_id="evidence-1",
        run_id="run-1",
        market="CN",
        ticker="600519.SH",
        data_domain="daily_bar",
        provider="akshare+tushare",
        provider_ticker="akshare:600519;tushare:600519.SH",
        source_updated_at=now,
        observed_at=now,
        normalized_payload={"price_diff_pct": {"close": 0.0}},
        raw_field_mapping={"close": ["收盘", "close"]},
        quality_flags=["unit_unverified:amount"],
        cross_source_status="matched",
        gate_status="warn",
        allowed_downstream=["vectorbt", "alphasift_exploratory"],
        notes="unit test",
    )

    data = evidence.to_dict()

    assert data["source_updated_at"] == "2026-07-04T00:00:00+00:00"
    assert data["allowed_downstream"] == ["vectorbt", "alphasift_exploratory"]


def test_allowed_downstream_controls_reuse_adapters() -> None:
    daily_evidence = {
        "gate_status": "warn",
        "allowed_downstream": ["vectorbt", "alphasift_exploratory"],
    }
    blocked_evidence = {"gate_status": "block", "allowed_downstream": []}

    assert can_send_to_vectorbt(daily_evidence) is True
    assert can_send_to_alphasift(daily_evidence) is True
    assert can_send_to_vectorbt(blocked_evidence) is False
    assert can_send_to_alphasift(blocked_evidence) is False
