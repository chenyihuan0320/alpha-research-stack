from pathlib import Path

import scripts.probe_akshare as probe_akshare
from orchestrator.data.providers.akshare_provider import AkShareProviderError


def test_akshare_probe_writes_failure_report_when_provider_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    def raise_unavailable(*args, **kwargs):
        raise AkShareProviderError("AkShare unavailable in test")

    monkeypatch.setattr(probe_akshare, "fetch_cn_daily_bar_sample", raise_unavailable)
    monkeypatch.setattr(probe_akshare, "fetch_cn_valuation_sample", raise_unavailable)
    monkeypatch.setattr(probe_akshare, "fetch_hk_daily_bar_sample", raise_unavailable)
    monkeypatch.setattr(
        probe_akshare,
        "get_akshare_import_status",
        lambda: {"installed": False, "version": None, "error": "AkShare unavailable in test"},
    )
    monkeypatch.setattr(
        probe_akshare,
        "get_eastmoney_proxy_bypass_status",
        lambda: {
            "enabled": False,
            "mode": "auto",
            "configured_proxy_mode": "auto",
            "no_proxy": "<local>",
            "proxy_env_vars_present": "HTTP_PROXY, HTTPS_PROXY",
        },
    )

    universe = [
        {"market": "CN", "ticker": "600519.SH", "name": "Kweichow Moutai"},
        {"market": "HK", "ticker": "0700.HK", "name": "Tencent"},
        {"market": "US", "ticker": "AAPL", "name": "Apple"},
    ]
    records = probe_akshare.build_akshare_probe_records(universe)
    report_path = tmp_path / "akshare_probe_report.md"

    probe_akshare.write_report(records, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "akshare_installed: False" in text
    assert "eastmoney_proxy_bypass: False" in text
    assert "configured_proxy_mode: auto" in text
    assert "eastmoney_proxy_mode: auto" in text
    assert "AkShare unavailable in test" in text
    assert "| US | AAPL | daily_bar | skipped |" in text
