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
- `stock_zh_valuation_baidu`：A 股估值指标样本，当前 adapter 分别请求 `总市值`、`市盈率(TTM)` 和 `市净率`。

AkShare 接口和字段可能变动，真实 probe 报告必须记录实际字段覆盖和失败原因。

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

## 真实 Probe 记录

本节记录 2026-07-03 本地 provider validation 结果，报告文件为 `outputs/reports/akshare_probe_report.md`。

- AkShare 安装状态：已安装。
- AkShare 版本：`1.18.64`。
- 安装记录：首次安装 `.[dev,akshare]` 时出现依赖包哈希校验失败；重试后安装成功。
- 联网状态：部分成功。A 股估值接口成功返回样本；部分 A 股/港股日线接口成功返回样本，剩余日线请求在 Eastmoney 直连模式下仍出现 remote disconnect。
- Eastmoney 代理策略：默认使用 `direct_no_proxy`，调用 `stock_zh_a_hist` / `stock_hk_hist` 期间临时移除 `HTTP_PROXY`、`HTTPS_PROXY`、`http_proxy`、`https_proxy`、`ALL_PROXY`、`all_proxy`，并保留/补充 `NO_PROXY` 与 `no_proxy` 中的 Eastmoney 域名。调用结束后恢复原代理环境。
- 最新成功项：`stock_zh_valuation_baidu` 对 `600519.SH`、`000001.SZ`、`300750.SZ` 返回 A 股估值样本，每个 ticker 取到 5 行；`stock_zh_a_hist` 对 `600519.SH` 返回 A 股日线样本。
- 最新失败项：`stock_zh_a_hist` 对 `000001.SZ`、`300750.SZ` 和 `stock_hk_hist` 对 `0700.HK`、`9988.HK`、`3690.HK` 在 2 次尝试后仍被 Eastmoney 远端断开。
- 补充观察：多次 probe 中 Eastmoney 日线成功 ticker 会波动，说明问题不只是代理配置，也包括上游端点稳定性或当前网络到 Eastmoney API 的连接稳定性。
- 跳过项：美股仍按计划跳过，原因是 AkShare 不是第一阶段美股主 provider。

### 实际字段名与映射修正

| AkShare 接口 | 实际字段名 | 当前映射 | 状态 |
| --- | --- | --- | --- |
| `stock_zh_valuation_baidu` | `date`, `value` | 按 indicator 将 `value` 合并为 `market_cap`、`pe`、`pb` | 已修正 |
| `stock_zh_a_hist` | `日期`, `股票代码`, `开盘`, `收盘`, `最高`, `最低`, `成交量`, `成交额`, `振幅`, `涨跌幅`, `涨跌额`, `换手率` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`；qfq/hfq 时 `adj_close` 暂复用 `close` | 部分验证 |
| `stock_hk_hist` | `日期`, `开盘`, `收盘`, `最高`, `最低`, `成交量`, `成交额`, `振幅`, `涨跌幅`, `涨跌额`, `换手率` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`；不复权时 `adj_close` 为空 | 部分验证 |

本次根据真实 probe 做出的修正：

- 将 A 股估值 adapter 从不可用的 `stock_a_indicator_lg` 调整为 `stock_zh_valuation_baidu`。
- 将 Eastmoney 日线请求改为 provider validation 专用直连模式，并将 A 股日线真实请求窗口限制为最近 180 天，避免为了 tail(5) 拉取全量历史。
- `_to_float` 支持逗号、百分号、空字符串、`--`、`None`、`nan` 等常见 provider 值。
- `quality_flags` 增加或使用 `parse_error`、`unit_unverified`、`adjustment_unverified`、`provider_error`。
- `daily_bar.adjustment` 契约允许 `none`、`qfq`、`hfq`、`forward`、`backward`、`unknown`，adapter 仍需记录 provider 原始复权参数。

### 字段覆盖与 Quality Flags 样例

- A 股估值字段覆盖：`date`、`market_cap`、`pe`、`pb`。
- A 股估值缺失字段：`ps`、`dividend_yield`、`ev_ebitda`、`fcf_yield`。
- A 股日线成功样本字段覆盖：`date`、`open`、`high`、`low`、`close`、`adj_close`、`volume`、`amount`、`turnover`、`adjustment`。
- 港股日线成功样本字段覆盖：`date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`、`adjustment`；`adj_close` 为空。
- 样例 flags：`missing_field:ps`、`missing_field:dividend_yield`、`unit_unverified:market_cap`、`unit_unverified:dividend_yield`。
- 日线 quality flags：成功样本包含 `adjustment_unverified`、`unit_unverified:volume`、`unit_unverified:amount`、`unit_unverified:turnover`；失败样本包含 `provider_error`。

市值单位、股息率单位、复权口径仍不能直接进入策略假设，后续必须与 Tushare 或交易所/财报来源交叉验证。

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
