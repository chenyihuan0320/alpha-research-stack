from collections import Counter
from pathlib import Path

from orchestrator.data.provider_probe import build_probe_plan
from orchestrator.data.sample_universe import load_sample_universe


def test_build_probe_plan_generates_expected_counts() -> None:
    universe = load_sample_universe(Path("orchestrator/sample_data/universe_sample.csv"))
    rows = build_probe_plan(universe)
    statuses = Counter(row.status for row in rows)

    assert len(rows) == 30
    assert statuses["planned"] == 15
    assert statuses["needs_credentials"] == 6
    assert statuses["skipped"] == 9
    assert statuses["unavailable"] == 0


def test_build_probe_plan_for_cn_hk_us_expected_providers() -> None:
    universe = [
        {"market": "CN", "ticker": "600519.SH", "name": "Kweichow Moutai"},
        {"market": "HK", "ticker": "0700.HK", "name": "Tencent"},
        {"market": "US", "ticker": "AAPL", "name": "Apple"},
    ]

    rows = build_probe_plan(universe)
    keys = {(row.provider, row.market, row.ticker, row.capability, row.status) for row in rows}

    assert ("AkShare", "CN", "600519.SH", "daily_bar", "planned") in keys
    assert ("Tushare", "CN", "600519.SH", "fundamentals_snapshot", "needs_credentials") in keys
    assert ("AkShare", "HK", "0700.HK", "daily_bar", "planned") in keys
    assert ("OpenBB", "HK", "0700.HK", "daily_bar", "skipped") in keys
    assert ("EdgarTools", "US", "AAPL", "fundamentals_snapshot", "planned") in keys
    assert ("EdgarTools", "US", "AAPL", "event_record", "planned") in keys
    assert ("OpenBB", "US", "AAPL", "daily_bar", "skipped") in keys
    assert ("OpenBB", "US", "AAPL", "valuation_snapshot", "skipped") in keys


def test_probe_result_can_convert_to_dict() -> None:
    row = build_probe_plan([{"market": "HK", "ticker": "9988.HK", "name": "Alibaba HK"}])[0]

    data = row.to_dict()

    assert data["provider"] == "AkShare"
    assert data["market"] == "HK"
    assert data["required_fields"]
