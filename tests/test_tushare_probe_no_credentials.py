from pathlib import Path

import scripts.probe_tushare as probe_tushare


def test_tushare_probe_writes_needs_credentials_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    monkeypatch.setattr(
        probe_tushare,
        "get_tushare_import_status",
        lambda: {"installed": False, "version": None, "error": "not installed in test"},
    )
    universe = [
        {"market": "CN", "ticker": "600519.SH", "name": "Kweichow Moutai"},
        {"market": "HK", "ticker": "0700.HK", "name": "Tencent"},
    ]

    records = probe_tushare.build_tushare_probe_records(universe)
    report_path = tmp_path / "tushare_probe_report.md"
    probe_tushare.write_report(records, report_path)
    text = report_path.read_text(encoding="utf-8")

    assert len(records) == 4
    assert all(record.status == "needs_credentials" for record in records)
    assert "tushare_token_present: False" in text
    assert "needs_credentials:TUSHARE_TOKEN" in text
    assert "股票推荐" not in text
    assert "买入" not in text
    assert "卖出" not in text
