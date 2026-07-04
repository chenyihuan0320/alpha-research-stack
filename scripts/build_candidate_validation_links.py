#!/usr/bin/env python3
"""Build CandidateEvidence to ValidationEvidence linkage records."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.candidates.ledger import (  # noqa: E402
    DEFAULT_CANDIDATE_LEDGER_PATH,
    load_candidates,
)
from orchestrator.validation.ledger import (  # noqa: E402
    DEFAULT_VALIDATION_LEDGER_PATH,
    load_validations,
)
from orchestrator.validation.linkage import CandidateValidationLink  # noqa: E402
from orchestrator.validation.linkage_ledger import (  # noqa: E402
    DEFAULT_LINKAGE_LEDGER_PATH,
    append_link,
    load_links,
)


REPORT_PATH = Path("outputs/reports/candidate_validation_linkage.md")


def _match_key(market: str, ticker: str, date_value: str) -> tuple[str, str, str]:
    return market, ticker, date_value


def _validation_window(validation_ids: list[str], validation_by_id: dict[str, Any]) -> str:
    holding_periods = sorted(
        {
            str(validation_by_id[validation_id].holding_period)
            for validation_id in validation_ids
            if validation_id in validation_by_id
        }
    )
    if not holding_periods:
        return "holding_period=unknown"
    return "holding_period=" + ",".join(holding_periods)


def _make_link_id(run_id: str, market: str, ticker: str, date_value: str, status: str) -> str:
    return f"{run_id}:{market}:{ticker}:{date_value}:{status}"


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    boundary_text = "relationship ledger only; not investment output"
    lines = [
        "# Candidate Validation Linkage",
        "",
        f"- run_id: {result['run_id']}",
        f"- generated_at: {result['generated_at']}",
        f"- link_path: {result['link_path']}",
        "",
        "| item | status | detail |",
        "|---|---|---|",
        f"| candidates_loaded | {result['candidates_status']} | count={result['candidates_loaded']} |",
        f"| validations_loaded | {result['validations_status']} | count={result['validations_loaded']} |",
        f"| links_created | {result['links_status']} | count={result['links_created']} |",
        f"| orphan_validations | {result['orphan_status']} | count={result['orphan_validations']}; validation_orphaned_no_candidate |",
        f"| pending_candidates | {result['pending_status']} | count={result['pending_candidates']} |",
        f"| boundary | - | {boundary_text} |",
        "",
        "## Notes",
        "",
        "- CandidateValidationLink only connects existing candidate and validation records.",
        "- Baseline validations without candidates are marked missing_candidate.",
        "- No candidate records are created by this script.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_candidate_validation_links(
    *,
    candidate_path: str | Path = DEFAULT_CANDIDATE_LEDGER_PATH,
    validation_path: str | Path = DEFAULT_VALIDATION_LEDGER_PATH,
    link_path: str | Path = DEFAULT_LINKAGE_LEDGER_PATH,
    report_path: str | Path = REPORT_PATH,
) -> dict[str, Any]:
    candidates = load_candidates(candidate_path)
    validations = load_validations(validation_path)
    link_ledger_path = Path(link_path)
    if link_ledger_path.exists():
        link_ledger_path.unlink()

    run_id = "candidate-validation-linkage-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    generated_at = datetime.now(timezone.utc).isoformat()
    validations_by_key: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    validation_by_id = {row.validation_id: row for row in validations}
    for validation in validations:
        validations_by_key[_match_key(validation.market, validation.ticker, validation.event_date)].append(
            validation
        )

    matched_validation_ids: set[str] = set()
    linked_count = 0
    pending_candidates = 0

    for candidate in candidates:
        key = _match_key(candidate.market, candidate.ticker, candidate.candidate_date)
        matched_validations = validations_by_key.get(key, [])
        validation_ids = [validation.validation_id for validation in matched_validations]
        if validation_ids:
            matched_validation_ids.update(validation_ids)
            linkage_status = "linked"
            quality_flags = ["candidate_validation_linked"]
            linked_count += 1
        else:
            linkage_status = "pending_validation"
            quality_flags = ["missing_validation"]
            pending_candidates += 1
        append_link(
            CandidateValidationLink(
                link_id=_make_link_id(run_id, candidate.market, candidate.ticker, candidate.candidate_date, linkage_status),
                candidate_id=candidate.candidate_id,
                validation_ids=validation_ids,
                ticker=candidate.ticker,
                market=candidate.market,
                candidate_date=candidate.candidate_date,
                validation_window=_validation_window(validation_ids, validation_by_id),
                linkage_status=linkage_status,
                quality_flags=quality_flags,
                notes="Relationship only; not investment output.",
            ),
            link_ledger_path,
        )

    orphan_validations = 0
    for validation in validations:
        if validation.validation_id in matched_validation_ids:
            continue
        orphan_validations += 1
        append_link(
            CandidateValidationLink(
                link_id=_make_link_id(run_id, validation.market, validation.ticker, validation.event_date, "missing_candidate"),
                candidate_id="",
                validation_ids=[validation.validation_id],
                ticker=validation.ticker,
                market=validation.market,
                candidate_date=validation.event_date,
                validation_window=f"holding_period={validation.holding_period}",
                linkage_status="missing_candidate",
                quality_flags=["validation_orphaned_no_candidate"],
                notes="Baseline ValidationEvidence has no CandidateEvidence parent.",
            ),
            link_ledger_path,
        )

    links = load_links(link_ledger_path)
    result = {
        "run_id": run_id,
        "generated_at": generated_at,
        "candidate_path": str(candidate_path),
        "validation_path": str(validation_path),
        "link_path": str(link_ledger_path),
        "report_path": str(report_path),
        "candidates_loaded": len(candidates),
        "validations_loaded": len(validations),
        "links_created": len(links),
        "linked_count": linked_count,
        "orphan_validations": orphan_validations,
        "pending_candidates": pending_candidates,
        "candidates_status": "pass" if candidates else "warn",
        "validations_status": "pass" if validations else "warn",
        "links_status": "pass" if links else "warn",
        "orphan_status": "warn" if orphan_validations else "pass",
        "pending_status": "warn" if pending_candidates else "pass",
    }
    _write_report(result, Path(report_path))
    return result


def main() -> int:
    result = build_candidate_validation_links()
    print(f"candidates_loaded: {result['candidates_loaded']}")
    print(f"validations_loaded: {result['validations_loaded']}")
    print(f"links_created: {result['links_created']}")
    print(f"linked_count: {result['linked_count']}")
    print(f"orphan_validations: {result['orphan_validations']}")
    print(f"pending_candidates: {result['pending_candidates']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
