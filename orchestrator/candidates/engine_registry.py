"""Registry of candidate engine reuse targets."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CandidateEngineDefinition:
    engine_name: str
    role: str
    status: str
    engine_mode: str
    supported_markets: list[str]
    required_inputs: list[str]
    output_contract: str
    can_generate_candidate_evidence: bool
    is_candidate_discovery_engine: bool
    integration_cost: str
    accuracy_potential: str
    current_blocker: str
    next_action: str
    risks: list[str] = field(default_factory=list)


_ENGINES: dict[str, CandidateEngineDefinition] = {
    "alphasift": CandidateEngineDefinition(
        engine_name="alphasift",
        role="candidate_engine_candidate",
        status="pending_runtime",
        engine_mode="runtime",
        supported_markets=["CN"],
        required_inputs=["ProviderEvidence:daily_bar", "strategy_yaml", "runtime_dependencies"],
        output_contract="CandidateEvidence",
        can_generate_candidate_evidence=True,
        is_candidate_discovery_engine=True,
        integration_cost="medium",
        accuracy_potential="medium",
        current_blocker="runtime dependency missing: yaml/PyYAML; input mapping still needs runtime proof",
        next_action="Prepare isolated AlphaSift runtime dependencies and rerun no-LLM validation.",
        risks=[
            "small project surface",
            "runtime dependency gap",
            "ProviderEvidence input format not yet proven",
        ],
    ),
    "qlib": CandidateEngineDefinition(
        engine_name="qlib",
        role="factor_model_research_backbone",
        status="planned",
        engine_mode="planned",
        supported_markets=["CN", "US"],
        required_inputs=["normalized daily_bar panel", "feature store", "labels"],
        output_contract="CandidateEvidence",
        can_generate_candidate_evidence=True,
        is_candidate_discovery_engine=True,
        integration_cost="high",
        accuracy_potential="high",
        current_blocker="data format feasibility not validated",
        next_action="Design Qlib data format feasibility check after provider evidence is stable.",
        risks=[
            "heavier integration",
            "needs larger clean dataset",
            "model research can overfit without strict validation",
        ],
    ),
    "vectorbt_event_baseline": CandidateEngineDefinition(
        engine_name="vectorbt_event_baseline",
        role="validation_baseline",
        status="ready",
        engine_mode="planned",
        supported_markets=["CN", "HK", "US"],
        required_inputs=["ProviderEvidence:daily_bar", "event_dates"],
        output_contract="ValidationEvidence",
        can_generate_candidate_evidence=False,
        is_candidate_discovery_engine=False,
        integration_cost="low",
        accuracy_potential="baseline",
        current_blocker="not a discovery engine",
        next_action="Use only as event validation baseline after CandidateEvidence exists.",
        risks=[
            "does not solve discovery",
            "does not solve data quality",
        ],
    ),
    "openbb_research_input": CandidateEngineDefinition(
        engine_name="openbb_research_input",
        role="research_data_input",
        status="planned",
        engine_mode="planned",
        supported_markets=["US", "HK", "CN"],
        required_inputs=["symbol mapping", "provider license review"],
        output_contract="ProviderEvidence",
        can_generate_candidate_evidence=False,
        is_candidate_discovery_engine=False,
        integration_cost="medium",
        accuracy_potential="input_only",
        current_blocker="AGPL and provider coverage need review",
        next_action="Keep as optional data/research adapter, not candidate generator.",
        risks=["license constraints", "provider coverage variance"],
    ),
    "tradingagents_research_input": CandidateEngineDefinition(
        engine_name="tradingagents_research_input",
        role="deep_research_input",
        status="planned",
        engine_mode="planned",
        supported_markets=["US"],
        required_inputs=["CandidateEvidence", "research context"],
        output_contract="ResearchEvidence",
        can_generate_candidate_evidence=False,
        is_candidate_discovery_engine=False,
        integration_cost="high",
        accuracy_potential="research_only",
        current_blocker="LLM/deep research layer is out of current scope",
        next_action="Revisit only after candidate and validation layers are proven.",
        risks=["LLM dependency", "not a data quality or discovery source"],
    ),
}


def list_candidate_engines() -> list[CandidateEngineDefinition]:
    return list(_ENGINES.values())


def get_candidate_engine(name: str) -> CandidateEngineDefinition:
    try:
        return _ENGINES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown candidate engine: {name}") from exc
