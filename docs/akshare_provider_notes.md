# AkShare Provider Notes

本文记录 Alpha Research Stack 第一阶段 AkShare provider 的最小接入边界。AkShare 只用于验证数据源可用性、字段映射、缺失率、质量标记和失败原因，不产生股票推荐、候选评分、回测、LLM 日报或交易指令。

## 使用目标

- A 股：验证 `daily_bar` 和 `valuation_snapshot` 的字段覆盖。
- 港股：验证 `daily_bar` 的字段覆盖和 ticker mapping。
- 美股：第一阶段不使用 AkShare 作为主要 provider，美股行情/估值后续优先评估 OpenBB 或其他 provider，美股披露优先 EdgarTools。

## A 股 Ticker Mapping

项目内部 ticker 使用 `600519.SH`、`000001.SZ`、`300750.SZ`。

AkShare A 股历史行情接口 `stock_zh_a_hist` 使用 6 位数字 symbol：

| 项目 ticker | AkShare symbol |
| --- | --- |
| 600519.SH | 600519 |
| 000001.SZ | 000001 |
| 300750.SZ | 300750 |

## 港股 Ticker Mapping

项目内部 ticker 使用四位数字加 `.HK`，例如 `0700.HK`。AkShare 港股接口通常使用五位数字 symbol。

| 项目 ticker | AkShare symbol |
| --- | --- |
| 0700.HK | 00700 |
| 9988.HK | 09988 |
| 3690.HK | 03690 |

## 使用到的 AkShare 接口名称

- `stock_zh_a_hist`：A 股日线样本。
- `stock_hk_hist`：港股日线样本。
- `stock_a_indicator_lg`：A 股估值指标样本。

这些接口名来自当前 adapter 规划。AkShare 接口和字段可能变动，真实 probe 报告必须记录实际字段覆盖和失败原因。

## 字段映射表

### daily_bar

| 契约字段 | AkShare 候选字段 |
| --- | --- |
| date | 日期 / date / trade_date |
| open | 开盘 / open |
| high | 最高 / high |
| low | 最低 / low |
| close | 收盘 / close |
| adj_close | qfq/hfq 时复用 close；none 时为空 |
| volume | 成交量 / volume |
| amount | 成交额 / amount |
| turnover | 换手率 / turnover |
| source | 固定为 akshare |
| source_updated_at | adapter 当前 UTC 时间 |
| adjustment | qfq / hfq / none / unknown |
| quality_flags | adapter 根据缺失字段生成 |

### valuation_snapshot

| 契约字段 | AkShare 候选字段 |
| --- | --- |
| date | trade_date / 日期 / date |
| market_cap | total_mv / 总市值 / market_cap |
| pe | pe_ttm / pe / 市盈率 |
| pb | pb / 市净率 |
| ps | ps_ttm / ps / 市销率 |
| ev_ebitda | AkShare 当前 adapter 未直接提供，标记 missing_field |
| dividend_yield | dv_ttm / dv_ratio / 股息率 |
| fcf_yield | AkShare 当前 adapter 未直接提供，标记 missing_field |
| source | 固定为 akshare |
| source_updated_at | adapter 当前 UTC 时间 |
| quality_flags | adapter 根据缺失字段生成 |

## 已知风险

- 字段中文名变化：AkShare 返回列名可能随上游数据源变化。
- 复权口径：A 股 qfq/hfq/none 需要和 Tushare 交叉验证；港股复权支持不稳定。
- 单位：成交量、成交额、市值、估值指标单位需记录，不可默认跨 provider 一致。
- 限频：AkShare 无统一商业 SLA，源站限流或接口调整可能导致 probe 失败。
- 港股覆盖不稳定：港股 ticker 前导零、成交额币种和历史覆盖需要单独记录。
- 数据源质量：AkShare 是聚合接口，不能把单一接口结果直接视为事实。

## 为什么 AkShare 不能单独决定信号

- AkShare 不提供本项目需要的完整信号治理、样本外验证和复盘机制。
- 单一数据源无法发现字段错误、缺失、复权差异和单位差异。
- 估值和财务字段需要和 Tushare、交易所公告或 SEC/公司披露等来源交叉验证。
- 最终 confidence 必须来自数据质量、历史验证、样本外表现和复盘治理，不能由 provider 数据直接生成。

## 后续如何与 Tushare 交叉验证

1. 对相同 A 股 ticker 拉取最近日线，比较 date、open、high、low、close、volume、amount、turnover。
2. 比较复权口径：qfq/hfq/none 的价格序列和除权除息日附近差异。
3. 比较估值字段：market_cap、pe、pb、ps、dividend_yield 的单位和日期。
4. 比较财务字段：revenue、net_income、operating_cash_flow、assets、liabilities、equity。
5. 将差异写入字段覆盖报告和 `quality_flags`，在没有解释前不进入策略层。
