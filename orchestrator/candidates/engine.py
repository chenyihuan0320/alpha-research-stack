"""Candidate engine readiness abstractions.

This module does not run candidate engines. It only describes their input
boundary and readiness for later reuse validation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(slots=True)
class CandidateEngineInput:
    run_id: str
    market: str
    evidence_ids: list[str]
    evidence_domains: list[str]
    allowed_data_domains: list[str]
    engine_name: str
    engine_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateEngineResult:
    engine_name: str
    status: str
    supported_markets: list[str]
    required_inputs: list[str]
    output_contract: str
    can_generate_candidate_evidence: bool
    risks: list[str]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateEngineBenchmarkReport:
    run_id: str
    generated_at: str
    results: list[CandidateEngineResult] = field(default_factory=list)
    input_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _allowed_downstream(value: Any) -> list[str]:
    return [str(item) for item in (_field(value, "allowed_downstream", []) or [])]


def _is_allowed_for_any_candidate_path(value: Any) -> bool:
    allowed = set(_allowed_downstream(value))
    return bool(allowed & {"alphasift", "alphasift_exploratory", "vectorbt"})


def build_engine_input_from_provider_evidence(
    evidence_rows: Iterable[Any],
    *,
    engine_name: str,
    engine_mode: str,
) -> CandidateEngineInput:
    allowed_rows = [row for row in evidence_rows if _is_allowed_for_any_candidate_path(row)]
    evidence_ids = [str(_field(row, "evidence_id", "")) for row in allowed_rows]
    domains = sorted({str(_field(row, "data_domain", "")) for row in allowed_rows if _field(row, "data_domain", "")})
    markets = sorted({str(_field(row, "market", "")) for row in allowed_rows if _field(row, "market", "")})
    run_ids = [str(_field(row, "run_id", "")) for row in allowed_rows if _field(row, "run_id", "")]
    return CandidateEngineInput(
        run_id=run_ids[0] if run_ids else f"candidate-engine-benchmark-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        market=markets[0] if len(markets) == 1 else "mixed",
        evidence_ids=evidence_ids,
        evidence_domains=domains,
        allowed_data_domains=domains,
        engine_name=engine_name,
        engine_mode=engine_mode,
    )


def evaluate_candidate_engine_readiness(engine: Any) -> CandidateEngineResult:
    return CandidateEngineResult(
        engine_name=str(_field(engine, "engine_name")),
        status=str(_field(engine, "status")),
        supported_markets=list(_field(engine, "supported_markets", [])),
        required_inputs=list(_field(engine, "required_inputs", [])),
        output_contract=str(_field(engine, "output_contract")),
        can_generate_candidate_evidence=bool(_field(engine, "can_generate_candidate_evidence", False)),
        risks=list(_field(engine, "risks", [])),
        next_action=str(_field(engine, "next_action")),
    )


def compare_candidate_engines(
    *,
    engine_names: list[str] | None = None,
    evidence_rows: Iterable[Any] | None = None,
) -> CandidateEngineBenchmarkReport:
    from orchestrator.candidates.engine_registry import get_candidate_engine, list_candidate_engines

    engines = (
        [get_candidate_engine(name) for name in engine_names]
        if engine_names is not None
        else list_candidate_engines()
    )
    results = [evaluate_candidate_engine_readiness(engine) for engine in engines]
    input_summary: dict[str, Any] = {}
    if evidence_rows is not None:
        input_summary = build_engine_input_from_provider_evidence(
            evidence_rows,
            engine_name="benchmark",
            engine_mode="static",
        ).to_dict()
    return CandidateEngineBenchmarkReport(
        run_id=f"candidate-engine-benchmark-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        results=results,
        input_summary=input_summary,
    )
