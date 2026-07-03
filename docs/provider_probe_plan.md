# Provider Probe Plan

本计划用于验证第一阶段数据源的字段覆盖、缺失率、接口边界、凭证要求和集成风险。当前 Goal 只实现 dry-run probe，不联网、不安装依赖、不调用真实 provider。

## 样本 universe

| market | ticker | name | 说明 |
| --- | --- | --- | --- |
| CN | 600519.SH | Kweichow Moutai | A 股大市值消费 |
| CN | 000001.SZ | Ping An Bank | A 股金融 |
| CN | 300750.SZ | CATL | A 股创业板 |
| HK | 0700.HK | Tencent | 港股互联网 |
| HK | 9988.HK | Alibaba HK | 港股中概 |
| HK | 3690.HK | Meituan | 港股互联网 |
| US | AAPL | Apple | 美股 mega cap |
| US | NVDA | Nvidia | 美股半导体 |
| US | MSFT | Microsoft | 美股软件 |

## Ticker Mapping 风险

- A 股：AkShare、Tushare、Yahoo/OpenBB 可能分别使用 `600519`、`600519.SH`、`600519.SS`、`sh600519`。项目内部统一使用 `600519.SH` / `000001.SZ`。
- 港股：provider 可能使用 `0700.HK`、`00700.HK`、`700.HK`。项目内部统一使用四位数字加 `.HK`。
- 美股：普通 ticker 简单，但 share class、并购、退市和 ADR 需要后续单独处理。
- 所有 provider adapter 必须显式记录输入 ticker、provider ticker 和项目标准 ticker 的映射。

## AkShare 验证目标

- 验证目标：A 股和港股日线覆盖，A 股估值字段覆盖。
- 最小验证 ticker：`600519.SH`、`000001.SZ`、`300750.SZ`、`0700.HK`、`9988.HK`、`3690.HK`。
- 验证字段：
  - `daily_bar`：date、open、high、low、close、adj_close、volume、amount、turnover、adjustment。
  - `valuation_snapshot`：date、market_cap、pe、pb、ps、dividend_yield。
- 凭证要求：通常不需要 token；需验证接口限频、字段变动和源站稳定性。
- 可能失败原因：接口字段变更、源站限流、港股接口覆盖不足、复权口径不清、单位不一致。
- 不通过时替代方案：A 股用 Tushare Pro 补充；港股用 OpenBB 或后续单独选择港股 provider。

## Tushare 验证目标

- 验证目标：A 股日线、财务、估值和交易日历的结构化覆盖。
- 最小验证 ticker：`600519.SH`、`000001.SZ`、`300750.SZ`。
- 验证字段：
  - `daily_bar`：date、open、high、low、close、volume、amount、turnover、adjustment。
  - `fundamentals_snapshot`：period_end、fiscal_period、report_date、revenue、net_income、operating_cash_flow、total_assets、total_liabilities、total_equity、shares_outstanding。
  - `valuation_snapshot`：date、market_cap、pe、pb、ps、dividend_yield。
- 凭证要求：需要 Tushare token；真实 token 只能通过环境变量或 `.env.example` 描述，不能提交。
- 可能失败原因：token 缺失、积分或权限不足、限频、财务字段口径不同、复权字段需要额外接口。
- 不通过时替代方案：A 股行情和估值用 AkShare；财务字段用交易所公告、Eastmoney/同花顺接口或后续商业数据源评估。

## EdgarTools 验证目标

- 验证目标：美股 SEC 披露、财务报表和事件记录。
- 最小验证 ticker：`AAPL`、`NVDA`、`MSFT`。
- 验证字段：
  - `fundamentals_snapshot`：period_end、fiscal_period、report_date、revenue、gross_profit、operating_income、net_income、operating_cash_flow、free_cash_flow、total_assets、total_liabilities、total_equity、debt、shares_outstanding。
  - `event_record`：event_date、event_type、title、summary、url。
- 凭证要求：通常不需要 API key，但 SEC 访问需要合理 user identity、限频和缓存策略；真实接入前需确认配置方式。
- 可能失败原因：公司 ticker 到 CIK 映射失败、XBRL tag 差异、财年口径差异、SEC 限流、非标准披露。
- 不通过时替代方案：OpenBB/FMP/YFinance 等补财务摘要；SEC 原始文件解析作为 fallback。

## OpenBB 验证目标

- 验证目标：美股/跨资产行情、估值和港股覆盖的可行性。
- 最小验证 ticker：`AAPL`、`NVDA`、`MSFT`、`0700.HK`、`9988.HK`、`3690.HK`。
- 验证字段：
  - `daily_bar`：date、open、high、low、close、adj_close、volume。
  - `valuation_snapshot`：date、market_cap、pe、pb、ps、dividend_yield。
- 凭证要求：取决于 OpenBB provider；同时需确认 AGPL-3.0-only 许可证对本项目使用和分发的影响。
- 可能失败原因：许可证未确认、provider 需要 token、港股覆盖不足、字段名跨 provider 不稳定。
- 不通过时替代方案：美股行情用 yfinance 或 Nasdaq/Stooq 等单独 provider；港股改用 AkShare 或专门港股数据源。

## 港股验证目标

- 验证目标：先验证 `daily_bar` 覆盖和 ticker mapping，不把港股财务/估值作为第一阶段强依赖。
- 最小验证 ticker：`0700.HK`、`9988.HK`、`3690.HK`。
- 验证字段：date、open、high、low、close、volume、amount、currency、source_updated_at。
- 凭证要求：AkShare 通常无 token；OpenBB 取决于 provider 和许可证确认。
- 可能失败原因：ticker 前导零、成交额单位、HKD/CNY 双柜台、provider 覆盖不完整。
- 不通过时替代方案：只保留港股 security_master 和日线观察，不进入候选发现；后续评估专门港股数据源。

## Dry-run Probe 输出要求

- 只生成计划，不调用真实接口。
- 每个计划项记录 provider、market、ticker、capability、status、required_fields 和 notes。
- status 只能是 `planned`、`skipped`、`needs_credentials`、`unavailable`。
- 第一阶段真实接入前，必须把 dry-run 计划升级为字段覆盖记录。
