"""JSONL provider evidence ledger."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from orchestrator.evidence.models import ProviderEvidence


DEFAULT_LEDGER_PATH = Path("outputs/evidence/provider_evidence.jsonl")


def append_evidence(evidence: ProviderEvidence, path: str | Path = DEFAULT_LEDGER_PATH) -> None:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evidence.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_evidence(path: str | Path = DEFAULT_LEDGER_PATH) -> list[ProviderEvidence]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[ProviderEvidence] = []
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(ProviderEvidence.from_dict(json.loads(line)))
    return rows


def filter_evidence(
    *,
    market: str | None = None,
    ticker: str | None = None,
    data_domain: str | None = None,
    gate_status: str | None = None,
    path: str | Path = DEFAULT_LEDGER_PATH,
) -> list[ProviderEvidence]:
    rows = load_evidence(path)
    if market is not None:
        rows = [row for row in rows if row.market == market]
    if ticker is not None:
        rows = [row for row in rows if row.ticker == ticker]
    if data_domain is not None:
        rows = [row for row in rows if row.data_domain == data_domain]
    if gate_status is not None:
        rows = [row for row in rows if row.gate_status == gate_status]
    return rows


def summarize_evidence(path: str | Path = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    rows = load_evidence(path)
    by_domain = Counter(row.data_domain for row in rows)
    by_gate = Counter(row.gate_status for row in rows)
    by_cross_source = Counter(row.cross_source_status for row in rows)
    downstream = Counter(
        downstream_name
        for row in rows
        for downstream_name in row.allowed_downstream
    )
    return {
        "total": len(rows),
        "by_domain": dict(sorted(by_domain.items())),
        "by_gate_status": dict(sorted(by_gate.items())),
        "by_cross_source_status": dict(sorted(by_cross_source.items())),
        "allowed_downstream": dict(sorted(downstream.items())),
    }
