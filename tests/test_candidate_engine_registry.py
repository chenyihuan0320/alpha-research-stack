from __future__ import annotations

from orchestrator.candidates.engine import (
    build_engine_input_from_provider_evidence,
    compare_candidate_engines,
    evaluate_candidate_engine_readiness,
)
from orchestrator.candidates.engine_registry import get_candidate_engine, list_candidate_engines


def test_registry_contains_required_engines() -> None:
    names = {engine.engine_name for engine in list_candidate_engines()}

    assert "alphasift" in names
    assert "qlib" in names
    assert "vectorbt_event_baseline" in names
    assert "openbb_research_input" in names
    assert "tradingagents_research_input" in names


def test_alphasift_and_qlib_readiness_statuses() -> None:
    alphasift = evaluate_candidate_engine_readiness(get_candidate_engine("alphasift"))
    qlib = evaluate_candidate_engine_readiness(get_candidate_engine("qlib"))

    assert alphasift.status == "pending_runtime"
    assert qlib.status == "planned"


def test_vectorbt_event_baseline_is_not_candidate_discovery_main_engine() -> None:
    vectorbt = get_candidate_engine("vectorbt_event_baseline")
    result = evaluate_candidate_engine_readiness(vectorbt)

    assert vectorbt.role == "validation_baseline"
    assert vectorbt.is_candidate_discovery_engine is False
    assert result.can_generate_candidate_evidence is False


def test_build_engine_input_from_provider_evidence_uses_allowed_evidence_only() -> None:
    evidence_rows = [
        {
            "evidence_id": "ev-1",
            "market": "CN",
            "data_domain": "daily_bar",
            "allowed_downstream": ["alphasift_exploratory"],
        },
        {
            "evidence_id": "ev-2",
            "market": "CN",
            "data_domain": "valuation",
            "allowed_downstream": [],
        },
    ]

    engine_input = build_engine_input_from_provider_evidence(
        evidence_rows,
        engine_name="alphasift",
        engine_mode="static",
    )

    assert engine_input.market == "CN"
    assert engine_input.evidence_ids == ["ev-1"]
    assert engine_input.evidence_domains == ["daily_bar"]
    assert engine_input.allowed_data_domains == ["daily_bar"]


def test_compare_candidate_engines_has_no_forbidden_decision_language() -> None:
    report = compare_candidate_engines(
        engine_names=["alphasift", "qlib", "vectorbt_event_baseline"],
    )
    serialized = str([item.to_dict() for item in report.results]).lower()

    assert "recommendation" not in serialized
    assert "final signal" not in serialized
    assert "final confidence" not in serialized
