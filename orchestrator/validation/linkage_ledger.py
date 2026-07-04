"""JSONL ledger for CandidateValidationLink records."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from orchestrator.validation.linkage import CandidateValidationLink


DEFAULT_LINKAGE_LEDGER_PATH = Path("outputs/validation/candidate_validation_links.jsonl")


def append_link(
    link: CandidateValidationLink,
    path: str | Path = DEFAULT_LINKAGE_LEDGER_PATH,
) -> None:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(link.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_links(path: str | Path = DEFAULT_LINKAGE_LEDGER_PATH) -> list[CandidateValidationLink]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[CandidateValidationLink] = []
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(CandidateValidationLink.from_dict(json.loads(line)))
    return rows


def summarize_links(path: str | Path = DEFAULT_LINKAGE_LEDGER_PATH) -> dict[str, Any]:
    rows = load_links(path)
    by_status = Counter(row.linkage_status for row in rows)
    by_ticker = Counter(row.ticker for row in rows)
    return {
        "total": len(rows),
        "by_linkage_status": dict(sorted(by_status.items())),
        "by_ticker": dict(sorted(by_ticker.items())),
    }
