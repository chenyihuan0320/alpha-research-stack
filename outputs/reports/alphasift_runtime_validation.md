# AlphaSift Runtime Validation

- run_at: 2026-07-04T11:36:42.888548+00:00
- runtime_status: dependency_missing
- alphasift_path: references/alphasift
- command_attempted: `/home/andy/projects/alpha-research-stack/.venv/bin/python -m alphasift.cli screen ars_provider_evidence --market cn --max-output 3 --no-llm --no-post-analysis --no-daily-enrich --output outputs/alphasift_runtime/output/alphasift_screen.jsonl --jsonl`
- exit_code: 1
- stdout_path: outputs/alphasift_runtime/logs/alphasift_stdout.log
- stderr_path: outputs/alphasift_runtime/logs/alphasift_stderr.log
- raw_output_path: outputs/alphasift_runtime/output/alphasift_screen.jsonl
- candidate_evidence_written: False
- candidates_written_count: 0

## Input Files Generated

- universe: outputs/alphasift_runtime/input/universe.csv
- provider_evidence_mapping: outputs/alphasift_runtime/input/provider_evidence_mapping.json
- strategy: outputs/alphasift_runtime/input/ars_provider_evidence.yaml

## Output Files Detected

- none

## Error Summary

Traceback (most recent call last): File "<frozen runpy>", line 189, in _run_module_as_main File "<frozen runpy>", line 112, in _get_module_details File "/home/andy/projects/alpha-research-stack/references/alphasift/alphasift/__init__.py", line 6, in <module> from alphasift.pipeline import screen File "/home/andy/projects/alpha-research-stack/references/alphasift/alphasift/pipeline.py", line 36, in <module> from alphasift.strategy import load_all_strategies File "/home/andy/projects/alpha-research-stack/references/alphasift/alphasift/strategy.py", line 9, in <module> import yaml ModuleNotFoundError: No module named 'yaml'

## Parse Warnings

- none

## Boundary

- This is runtime reuse validation only.
- It is not a stock recommendation.
- It is not a final signal.
- It does not produce final confidence.
- It is not a backtest.
- It does not use LLM ranking.
- It is not automated trading.
