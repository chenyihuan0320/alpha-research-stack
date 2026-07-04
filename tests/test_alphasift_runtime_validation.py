from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.candidates.ledger import load_candidates
from orchestrator.evidence.ledger import append_evidence
from orchestrator.evidence.models import ProviderEvidence


def _write_evidence(path: Path) -> None:
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-600519-daily",
            run_id="run-010",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"compared_fields": ["open", "close"], "price_diff_pct": {"close": 0.0}},
            raw_field_mapping={"akshare": {"close": "收盘"}, "tushare": {"close": "close"}},
            quality_flags=["adjustment_unverified:none"],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["alphasift_exploratory"],
            notes="test evidence",
        ),
        path,
    )


def test_no_alphasift_path_reports_missing_repo(tmp_path, monkeypatch) -> None:
    import scripts.run_alphasift_no_llm_validation as runtime

    evidence_path = tmp_path / "provider_evidence.jsonl"
    report_path = tmp_path / "runtime.md"
    runtime_dir = tmp_path / "runtime"
    _write_evidence(evidence_path)
    monkeypatch.delenv("ALPHASIFT_PATH", raising=False)

    result = runtime.run_alphasift_no_llm_validation(
        evidence_path=evidence_path,
        runtime_dir=runtime_dir,
        report_path=report_path,
        candidate_path=tmp_path / "candidate_evidence.jsonl",
        local_project_paths=[tmp_path / "missing"],
        execute_command=False,
    )

    assert result["runtime_status"] == "missing_repo"
    assert result["candidate_evidence_written"] is False
    assert "missing_repo" in report_path.read_text(encoding="utf-8")


def test_alphasift_path_without_cli_reports_cli_not_found(tmp_path) -> None:
    import scripts.run_alphasift_no_llm_validation as runtime

    evidence_path = tmp_path / "provider_evidence.jsonl"
    alphasift_path = tmp_path / "alphasift"
    alphasift_path.mkdir()
    (alphasift_path / "README.md").write_text("AlphaSift", encoding="utf-8")
    _write_evidence(evidence_path)

    result = runtime.run_alphasift_no_llm_validation(
        evidence_path=evidence_path,
        runtime_dir=tmp_path / "runtime",
        report_path=tmp_path / "runtime.md",
        candidate_path=tmp_path / "candidate_evidence.jsonl",
        local_project_paths=[alphasift_path],
        execute_command=False,
    )

    assert result["runtime_status"] == "cli_not_found"


def test_dependency_missing_is_reported(tmp_path) -> None:
    import scripts.run_alphasift_no_llm_validation as runtime

    evidence_path = tmp_path / "provider_evidence.jsonl"
    alphasift_path = tmp_path / "alphasift"
    (alphasift_path / "alphasift").mkdir(parents=True)
    (alphasift_path / "alphasift" / "cli.py").write_text("# cli", encoding="utf-8")
    _write_evidence(evidence_path)

    result = runtime.run_alphasift_no_llm_validation(
        evidence_path=evidence_path,
        runtime_dir=tmp_path / "runtime",
        report_path=tmp_path / "runtime.md",
        candidate_path=tmp_path / "candidate_evidence.jsonl",
        local_project_paths=[alphasift_path],
        command_runner=lambda *args, **kwargs: runtime.CommandResult(
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'pandas'",
        ),
    )

    assert result["runtime_status"] == "dependency_missing"
    assert "pandas" in result["error_summary"]


def test_fake_successful_raw_output_maps_candidate_evidence(tmp_path) -> None:
    import scripts.run_alphasift_no_llm_validation as runtime

    evidence_path = tmp_path / "provider_evidence.jsonl"
    alphasift_path = tmp_path / "alphasift"
    (alphasift_path / "alphasift").mkdir(parents=True)
    (alphasift_path / "alphasift" / "cli.py").write_text("# cli", encoding="utf-8")
    _write_evidence(evidence_path)

    def runner(command, *, cwd, env, stdout_path, stderr_path):
        output_path = Path(command[command.index("--output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "\n".join(
                [
                    json.dumps({"type": "run", "run_id": "as-run-1", "strategy": "ars_provider_evidence"}),
                    json.dumps(
                        {
                            "type": "pick",
                            "run_id": "as-run-1",
                            "code": "600519",
                            "name": "Kweichow Moutai",
                            "score": 71.5,
                            "reasons": ["runtime test reason"],
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        stdout_path.write_text("ok", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return runtime.CommandResult(exit_code=0, stdout="ok", stderr="")

    candidate_path = tmp_path / "candidate_evidence.jsonl"
    result = runtime.run_alphasift_no_llm_validation(
        evidence_path=evidence_path,
        runtime_dir=tmp_path / "runtime",
        report_path=tmp_path / "runtime.md",
        candidate_path=candidate_path,
        local_project_paths=[alphasift_path],
        command_runner=runner,
    )

    candidates = load_candidates(candidate_path)
    assert result["runtime_status"] == "success"
    assert result["candidate_evidence_written"] is True
    assert len(candidates) == 1
    assert candidates[0].candidate_source == "alphasift"
    assert candidates[0].ticker == "600519.SH"
    assert candidates[0].provider_evidence_ids == ["ev-600519-daily"]
    assert candidates[0].allowed_next_steps == ["research", "vectorbt_validation"]


def test_parse_failed_does_not_write_candidate_evidence(tmp_path) -> None:
    import scripts.run_alphasift_no_llm_validation as runtime

    evidence_path = tmp_path / "provider_evidence.jsonl"
    alphasift_path = tmp_path / "alphasift"
    (alphasift_path / "alphasift").mkdir(parents=True)
    (alphasift_path / "alphasift" / "cli.py").write_text("# cli", encoding="utf-8")
    _write_evidence(evidence_path)

    def runner(command, *, cwd, env, stdout_path, stderr_path):
        output_path = Path(command[command.index("--output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("not-json\n", encoding="utf-8")
        stdout_path.write_text("not-json", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return runtime.CommandResult(exit_code=0, stdout="not-json", stderr="")

    candidate_path = tmp_path / "candidate_evidence.jsonl"
    result = runtime.run_alphasift_no_llm_validation(
        evidence_path=evidence_path,
        runtime_dir=tmp_path / "runtime",
        report_path=tmp_path / "runtime.md",
        candidate_path=candidate_path,
        local_project_paths=[alphasift_path],
        command_runner=runner,
    )

    assert result["runtime_status"] == "parse_failed"
    assert result["candidate_evidence_written"] is False
    assert not candidate_path.exists()
