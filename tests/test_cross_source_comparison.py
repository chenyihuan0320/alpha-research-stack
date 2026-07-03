from pathlib import Path

import scripts.compare_akshare_tushare as comparison


def test_comparison_writes_pending_credentials_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    universe = [
        {"market": "CN", "ticker": "600519.SH", "name": "Kweichow Moutai"},
        {"market": "CN", "ticker": "000001.SZ", "name": "Ping An Bank"},
        {"market": "US", "ticker": "AAPL", "name": "Apple"},
    ]

    records = comparison.build_comparison_records(universe)
    report_path = tmp_path / "akshare_tushare_comparison.md"
    comparison.write_report(records, report_path)
    text = report_path.read_text(encoding="utf-8")

    assert len(records) == 2
    assert all(record.status == "pending_credentials" for record in records)
    assert all(record.gate_status == "pending_credentials" for record in records)
    assert all(record.allow_candidate_discovery is False for record in records)
    assert "pending_credentials:TUSHARE_TOKEN" in text
    assert "买入" not in text
    assert "卖出" not in text
    assert "buy now" not in text.lower()
    assert "sell now" not in text.lower()


def test_pct_diff_uses_tushare_as_denominator() -> None:
    assert comparison._pct_diff(102, 100) == 2.0
    assert comparison._pct_diff(100, 0) is None
