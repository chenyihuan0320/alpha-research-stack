from datetime import UTC, datetime

from orchestrator.evidence.ledger import (
    append_evidence,
    filter_evidence,
    load_evidence,
    summarize_evidence,
)
from orchestrator.evidence.models import ProviderEvidence


def _evidence(ticker: str, data_domain: str, gate_status: str) -> ProviderEvidence:
    now = datetime(2026, 7, 4, tzinfo=UTC)
    return ProviderEvidence(
        evidence_id=f"test:{ticker}:{data_domain}",
        run_id="test",
        market="CN",
        ticker=ticker,
        data_domain=data_domain,
        provider="unit-test",
        provider_ticker=ticker,
        source_updated_at=now,
        observed_at=now,
        normalized_payload={"sample_summary": "unit test"},
        raw_field_mapping={},
        quality_flags=[],
        cross_source_status="matched",
        gate_status=gate_status,
        allowed_downstream=["vectorbt"] if data_domain == "daily_bar" else [],
        notes=None,
    )


def test_ledger_append_load_filter_and_summarize(tmp_path) -> None:
    path = tmp_path / "provider_evidence.jsonl"
    append_evidence(_evidence("600519.SH", "daily_bar", "warn"), path)
    append_evidence(_evidence("600519.SH", "valuation", "block"), path)
    append_evidence(_evidence("000001.SZ", "daily_bar", "warn"), path)

    rows = load_evidence(path)
    filtered = filter_evidence(ticker="600519.SH", data_domain="daily_bar", path=path)
    summary = summarize_evidence(path)

    assert len(rows) == 3
    assert len(filtered) == 1
    assert filtered[0].ticker == "600519.SH"
    assert summary["total"] == 3
    assert summary["by_domain"]["daily_bar"] == 2
    assert summary["by_gate_status"]["block"] == 1
    assert summary["allowed_downstream"]["vectorbt"] == 2
