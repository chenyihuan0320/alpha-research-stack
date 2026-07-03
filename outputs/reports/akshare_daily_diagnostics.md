# AkShare Daily Diagnostics

- 运行时间: 2026-07-03T08:52:01.032850+00:00
- Python executable: /home/andy/projects/alpha-research-stack/.venv/bin/python
- AkShare version: 1.18.64
- proxy_env_vars_present: HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy
- no_proxy: <local>
- alternative_daily_functions: stock_zh_a_daily, stock_hk_daily
- recommended_proxy_mode: none: both proxy modes failed in this environment
- note: This diagnostic only tests data provider connectivity and field coverage. It does not produce signals, scores, backtests, LLM output, reports, or trading instructions.

## Results

| market | ticker | interface | proxy_mode | status | shape | columns | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CN | 600519.SH | stock_zh_a_hist | respect_env_proxy | failed | - | - | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&secid=1.600519&beg=20260404&end=20260703 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| CN | 000001.SZ | stock_zh_a_hist | respect_env_proxy | failed | - | - | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&secid=0.000001&beg=20260404&end=20260703 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| HK | 0700.HK | stock_hk_hist | respect_env_proxy | failed | - | - | HTTPSConnectionPool(host='33.push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?secid=116.00700&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&klt=101&fqt=0&end=20500000&lmt=1000000 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| CN | 600519.SH | stock_zh_a_hist | direct_no_proxy | failed | - | - | ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| CN | 000001.SZ | stock_zh_a_hist | direct_no_proxy | failed | - | - | ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| HK | 0700.HK | stock_hk_hist | direct_no_proxy | failed | - | - | ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |

## Interpretation

- If both proxy modes fail, AkShare daily bars should be treated as unavailable for this environment.
- If only one proxy mode succeeds, set `ARS_AKSHARE_EASTMONEY_PROXY_MODE` to that mode for provider validation.
- If success varies across tickers or runs, treat Eastmoney daily-bar coverage as unstable and cross-check with another provider before strategy work.
