# Candidate Validation Linkage

- run_id: candidate-validation-linkage-20260704T143935Z
- generated_at: 2026-07-04T14:39:35.099507+00:00
- link_path: outputs/validation/candidate_validation_links.jsonl

| item | status | detail |
|---|---|---|
| candidates_loaded | warn | count=0 |
| validations_loaded | pass | count=3 |
| links_created | pass | count=3 |
| orphan_validations | warn | count=3; validation_orphaned_no_candidate |
| pending_candidates | pass | count=0 |
| boundary | - | relationship ledger only; not investment output |

## Notes

- CandidateValidationLink only connects existing candidate and validation records.
- Baseline validations without candidates are marked missing_candidate.
- No candidate records are created by this script.
