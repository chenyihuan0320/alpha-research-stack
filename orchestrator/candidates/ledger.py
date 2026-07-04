"""JSONL ledger for candidate evidence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from orchestrator.candidates.models import CandidateEvidence


DEFAULT_CANDIDATE_LEDGER_PATH = Path("outputs/candidates/candidate_evidence.jsonl")


def append_candidate(
    candidate: CandidateEvidence,
    path: str | Path = DEFAULT_CANDIDATE_LEDGER_PATH,
) -> None:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(candidate.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_candidates(path: str | Path = DEFAULT_CANDIDATE_LEDGER_PATH) -> list[CandidateEvidence]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[CandidateEvidence] = []
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(CandidateEvidence.from_dict(json.loads(line)))
    return rows


def summarize_candidates(path: str | Path = DEFAULT_CANDIDATE_LEDGER_PATH) -> dict[str, Any]:
    rows = load_candidates(path)
    by_source = Counter(row.candidate_source for row in rows)
    by_gate = Counter(row.gate_status for row in rows)
    by_direction = Counter(row.candidate_direction for row in rows)
    next_steps = Counter(step for row in rows for step in row.allowed_next_steps)
    return {
        "total": len(rows),
        "by_source": dict(sorted(by_source.items())),
        "by_gate_status": dict(sorted(by_gate.items())),
        "by_direction": dict(sorted(by_direction.items())),
        "allowed_next_steps": dict(sorted(next_steps.items())),
    }
