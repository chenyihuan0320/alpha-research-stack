from __future__ import annotations

from orchestrator.validation.linkage import CandidateValidationLink
from orchestrator.validation.linkage_ledger import append_link, load_links, summarize_links


def test_candidate_validation_link_round_trip() -> None:
    link = CandidateValidationLink(
        link_id="link-1",
        candidate_id="cand-1",
        validation_ids=["val-1"],
        ticker="600519.SH",
        market="CN",
        candidate_date="2026-07-02",
        validation_window="holding_period=1",
        linkage_status="linked",
        quality_flags=["validation_linked"],
        notes="Relationship only; not investment output.",
    )

    restored = CandidateValidationLink.from_dict(link.to_dict())

    assert restored == link
    assert "confidence" not in link.to_dict()


def test_linkage_ledger_append_load_and_summarize(tmp_path) -> None:
    path = tmp_path / "candidate_validation_links.jsonl"
    append_link(
        CandidateValidationLink(
            link_id="link-1",
            candidate_id="cand-1",
            validation_ids=["val-1"],
            ticker="600519.SH",
            market="CN",
            candidate_date="2026-07-02",
            validation_window="holding_period=1",
            linkage_status="linked",
            quality_flags=[],
            notes=None,
        ),
        path,
    )
    append_link(
        CandidateValidationLink(
            link_id="link-2",
            candidate_id="cand-2",
            validation_ids=[],
            ticker="000001.SZ",
            market="CN",
            candidate_date="2026-07-02",
            validation_window="holding_period=1",
            linkage_status="pending_validation",
            quality_flags=["missing_validation"],
            notes=None,
        ),
        path,
    )

    rows = load_links(path)
    summary = summarize_links(path)

    assert [row.linkage_status for row in rows] == ["linked", "pending_validation"]
    assert summary["total"] == 2
    assert summary["by_linkage_status"] == {"linked": 1, "pending_validation": 1}
    assert summary["by_ticker"] == {"000001.SZ": 1, "600519.SH": 1}
