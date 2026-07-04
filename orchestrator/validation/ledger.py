"""JSONL ValidationEvidence ledger."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from orchestrator.validation.models import ValidationEvidence


DEFAULT_VALIDATION_LEDGER_PATH = Path("outputs/validation/validation_evidence.jsonl")


def append_validation(
    validation: ValidationEvidence,
    path: str | Path = DEFAULT_VALIDATION_LEDGER_PATH,
) -> None:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(validation.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_validations(path: str | Path = DEFAULT_VALIDATION_LEDGER_PATH) -> list[ValidationEvidence]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[ValidationEvidence] = []
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(ValidationEvidence.from_dict(json.loads(line)))
    return rows


def summarize_validations(path: str | Path = DEFAULT_VALIDATION_LEDGER_PATH) -> dict[str, Any]:
    rows = load_validations(path)
    by_source = Counter(row.validation_source for row in rows)
    by_gate = Counter(row.gate_status for row in rows)
    by_ticker = Counter(row.ticker for row in rows)
    return {
        "total": len(rows),
        "by_source": dict(sorted(by_source.items())),
        "by_gate_status": dict(sorted(by_gate.items())),
        "by_ticker": dict(sorted(by_ticker.items())),
    }
