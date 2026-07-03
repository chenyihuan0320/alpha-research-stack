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
- `stock_zh_a_daily`：A 股日线样本，新浪财经源，当前作为默认日线主路径。
- `stock_hk_daily`：港股日线样本，新浪财经源，当前作为默认日线主路径。
- `stock_zh_valuation_baidu`：A 股估值指标样本，当前 adapter 分别请求 `总市值`、`市盈率(TTM)` 和 `市净率`。
- `stock_zh_valuation_comparison_em` 的原始东财 JSON：补充 `市销率-TTM` 和可用时的 `EV/EBITDA-24A`。
- `stock_history_dividend_detail` + 新浪日线 close：估算 TTM 股息率。

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
| ps | 东财估值比较 `PS_TTM`，标记 `source_date_unverified` |
| ev_ebitda | 东财估值比较 `QYBS` / `EV/EBITDA-24A`，可用时填充；银行等行业可能缺失 |
| dividend_yield | 新浪分红明细近 365 日现金分红 / 最新日线 close 估算，标记 `estimated_value` |
| fcf_yield | 当前 adapter 不填充，需完整自由现金流口径后再计算 |
| source | 固定为 akshare |
| source_updated_at | adapter 当前 UTC 时间 |
| quality_flags | adapter 根据缺失字段生成 |

## 真实 Probe 记录

本节记录 2026-07-03 本地 provider validation 结果，报告文件为 `outputs/reports/akshare_probe_report.md`。

- AkShare 安装状态：已安装。
- AkShare 版本：`1.18.64`。
- 安装记录：首次安装 `.[dev,akshare]` 时出现依赖包哈希校验失败；重试后安装成功。
- 联网状态：部分成功。A 股估值接口成功返回样本；日线接口在当前环境中仍不稳定。
- Eastmoney 代理策略：默认使用 `auto`，先尝试 `respect_env_proxy`，失败后尝试 `direct_no_proxy`。可通过 `ARS_AKSHARE_EASTMONEY_PROXY_MODE` 显式设置 `auto`、`respect_env_proxy` 或 `direct_no_proxy`。
- 专用日线诊断结论：`outputs/reports/akshare_daily_diagnostics.md` 对 `600519.SH`、`000001.SZ`、`0700.HK` 分别测试 `respect_env_proxy` 与 `direct_no_proxy`，本次两种模式均失败。`respect_env_proxy` 失败表现为 proxy remote disconnect，`direct_no_proxy` 失败表现为 remote disconnect。
- 主 probe 结论：`scripts/probe_akshare.py` 的 auto 模式本轮出现间歇成功，`600519.SH` A 股日线和 `3690.HK` 港股日线成功，但 `000001.SZ`、`300750.SZ`、`0700.HK`、`9988.HK` 日线在两种模式下仍失败。
- 推荐 proxy mode：当前环境保留 `auto` 作为 provider validation 默认模式，因为它能同时记录代理与直连失败原因；但不能把 AkShare Eastmoney 日线视为稳定数据源。
- 明确降级结论：AkShare 日线暂不能作为稳定数据源，后续需要 Tushare 或其他 provider 做日线交叉验证。
- 估值成功项：`600519.SH`、`000001.SZ`、`300750.SZ` 均返回 A 股估值样本。`market_cap`、`pe`、`pb` 来自 Baidu 估值序列并对齐到共同最新日期；`ps` 来自东财估值比较；`dividend_yield` 为新浪分红和日线 close 估算；`ev_ebitda` 对部分行业可用，银行样本当前缺失；`fcf_yield` 仍不填充。
- 跳过项：美股仍按计划跳过，原因是 AkShare 不是第一阶段美股主 provider。

### 2026-07-03 Eastmoney Curl Fallback 修复记录

- 环境观察：切换日本代理后，Eastmoney kline endpoint 仍存在间歇断连；Python requests/AkShare 路径主要失败为 `RemoteDisconnected`，命令行 curl 路径在单次 diagnostics 中也可能返回 `curl: (52) Empty reply from server`。
- 代码修复：A 股/港股日线先尝试 AkShare 原生函数；失败后使用命令行 `curl` 直接请求 Eastmoney kline JSON，并解析为与 AkShare 同款中文字段。
- fallback 范围：curl fallback 只用于 Eastmoney 日线 provider validation，不用于估值、策略、候选评分、回测、LLM、日报或交易。
- host fallback：A 股和港股日线 fallback 会依次尝试 AkShare 默认 host 及少量 `*.push2his.eastmoney.com` 变体，并把每个 host 的失败原因写入报告。
- 最新 diagnostics：`outputs/reports/akshare_daily_diagnostics.md` 的单次小样本诊断仍显示 `600519.SH`、`000001.SZ`、`0700.HK` 在 `akshare_requests` 和 `curl_cli` 下均失败。
- 最新主 probe：`outputs/reports/akshare_probe_report.md` 显示 `success=7`、`failed=2`、`skipped=3`；`000001.SZ`、`300750.SZ`、`9988.HK`、`3690.HK` 日线样本成功，`600519.SH` 与 `0700.HK` 日线仍失败。
- transport 记录：报告中的 `effective_proxy_mode` 已区分 `respect_env_proxy/akshare_requests` 与 `respect_env_proxy/curl_cli`，避免把 AkShare requests 成功和 curl fallback 成功混为一谈。
- 当前结论：curl fallback 能提升日线 probe 成功率，但 Eastmoney 日线在当前代理链路下仍不稳定，不能作为唯一日线 provider。

### 2026-07-03 AkShare Sina 日线稳定化记录

- 新增配置：`ARS_AKSHARE_DAILY_SOURCE_MODE=sina_first|eastmoney_first|eastmoney_only|sina_only`，默认 `sina_first`。
- 默认路径：A 股日线优先使用 `stock_zh_a_daily`，ticker 映射为 `600519.SH -> sh600519`、`000001.SZ -> sz000001`；港股日线优先使用 `stock_hk_daily`，ticker 仍使用五位数字格式。
- fallback 路径：如果 `sina_first` 的新浪接口失败，再尝试 Eastmoney requests + curl fallback；可通过环境变量切换到 `eastmoney_first`、`eastmoney_only` 或 `sina_only` 做对照验证。
- 最新 diagnostics：`outputs/reports/akshare_daily_diagnostics.md` 显示 `akshare_sina` 对 `600519.SH`、`000001.SZ`、`0700.HK` 在代理和直连上下文均成功；Eastmoney requests 与 curl 仍失败。
- 最新主 probe：`outputs/reports/akshare_probe_report.md` 显示 `daily_source_mode=sina_first`，`success=9`、`failed=0`、`skipped=3`；A 股/港股日线和 A 股估值样本全部通过当前最小 universe。
- 当前结论：AkShare 可以作为第一阶段免费 provider validation 数据源使用，但默认日线主路径应是新浪接口，不应依赖 Eastmoney 单一路径。

### 实际字段名与映射修正

| AkShare 接口 | 实际字段名 | 当前映射 | 状态 |
| --- | --- | --- | --- |
| `stock_zh_valuation_baidu` | `date`, `value` | 按 indicator 将 `value` 合并为 `market_cap`、`pe`、`pb` | 已修正 |
| 东财估值比较原始 JSON | `PS_TTM`, `QYBS` | 补充 `ps`、`ev_ebitda`，字段日期为未验证当前快照 | 部分验证 |
| `stock_history_dividend_detail` + 新浪日线 | `派息`, `除权除息日`, `close` | 近 365 日每股现金分红 / 最新 close，估算 `dividend_yield` | 部分验证 |
| `stock_zh_a_hist` | `日期`, `股票代码`, `开盘`, `收盘`, `最高`, `最低`, `成交量`, `成交额`, `振幅`, `涨跌幅`, `涨跌额`, `换手率` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`；qfq/hfq 时 `adj_close` 暂复用 `close` | 部分验证 |
| `stock_hk_hist` | `日期`, `开盘`, `收盘`, `最高`, `最低`, `成交量`, `成交额`, `振幅`, `涨跌幅`, `涨跌额`, `换手率` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`；不复权时 `adj_close` 为空 | 部分验证 |
| `stock_zh_a_daily` | `date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `outstanding_share`, `turnover` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`turnover`；qfq/hfq 时 `adj_close` 暂复用 `close` | 已验证 |
| `stock_hk_daily` | `date`, `open`, `high`, `low`, `close`, `volume`, `amount` | 映射 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`；`turnover` 和 `adj_close` 为空并标记缺失 | 已验证 |
| Eastmoney curl fallback | `日期`, `开盘`, `收盘`, `最高`, `最低`, `成交量`, `成交额`, `振幅`, `涨跌幅`, `涨跌额`, `换手率`；A 股额外补 `股票代码` | 解析 Eastmoney `klines` 后复用 daily_bar 映射 | 部分验证 |

本次根据真实 probe 做出的修正：

- 将 A 股估值 adapter 从不可用的 `stock_a_indicator_lg` 调整为 `stock_zh_valuation_baidu`。
- 增加 Eastmoney proxy mode 配置和 auto fallback，并将 A 股日线真实请求窗口限制为最近 180 天，避免为了 tail(5) 拉取全量历史。
- 增加 Eastmoney curl CLI fallback 和 host fallback，用于 AkShare Python HTTP 路径失败时继续验证日线字段覆盖。
- 将 AkShare 日线默认模式改为 `sina_first`，解决当前环境下 Eastmoney 不稳定导致的 provider validation 失败。
- 将 A 股估值合并改为 latest common date snapshot，`market_cap`、`pe`、`pb` 只在共同最新日期上合并；没有共同日期时才降级为 latest-per-indicator 并写入 `asof_mismatch`。
- 补充 `ps`、部分 `ev_ebitda` 和估算 `dividend_yield`；这些字段不会静默进入策略层，分别带有 `source_date_unverified` 或 `estimated_value`。
- `_to_float` 支持逗号、百分号、空字符串、`--`、`None`、`nan` 等常见 provider 值。
- `quality_flags` 增加或使用 `parse_error`、`unit_unverified`、`adjustment_unverified`、`provider_error`、`asof_mismatch`、`partial_coverage`。
- `daily_bar.adjustment` 契约允许 `none`、`qfq`、`hfq`、`forward`、`backward`、`unknown`，adapter 仍需记录 provider 原始复权参数。

### 字段覆盖与 Quality Flags 样例

- A 股估值字段覆盖：`date`、`market_cap`、`pe`、`pb`、`ps`、`dividend_yield`；`ev_ebitda` 对 `600519.SH`、`300750.SZ` 可用，对 `000001.SZ` 当前缺失。
- A 股估值缺失字段：`fcf_yield` 当前全部缺失；银行等行业可能缺 `ev_ebitda`。
- A 股估值质量标记：`market_cap`、`pe`、`pb` 必须对齐共同日期；补充估值字段标记 `source_date_unverified`；估算股息率标记 `estimated_value`；缺失字段标记 `partial_coverage`。
- A 股日线成功样本字段覆盖：`date`、`open`、`high`、`low`、`close`、`adj_close`、`volume`、`amount`、`turnover`、`adjustment`。
- 港股新浪日线成功样本字段覆盖：`date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`adjustment`；`turnover` 和 `adj_close` 为空。
- 样例 flags：`source_date_unverified:ps`、`source_date_unverified:ev_ebitda`、`estimated_value:dividend_yield`、`missing_field:fcf_yield`、`unit_unverified:market_cap`。
- 日线 quality flags：成功样本包含 `adjustment_unverified`、`unit_unverified:volume`、`unit_unverified:amount`、`unit_unverified:turnover`；失败样本包含 `provider_error`。

市值单位、股息率单位、估值快照日期、复权口径仍不能直接进入策略假设，后续必须与 Tushare 或交易所/财报来源交叉验证。`fcf_yield` 必须在完成自由现金流字段验证后计算，不能由当前 AkShare 估值接口硬填。

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
3. 比较估值字段：market_cap、pe、pb、ps、ev_ebitda、dividend_yield 的单位和日期。
4. 用财务现金流和资本开支字段计算并验证 `fcf_yield`，不要从缺少口径说明的 provider 字段推断。
5. 比较财务字段：revenue、net_income、operating_cash_flow、assets、liabilities、equity。
6. 将差异写入字段覆盖报告和 `quality_flags`，在没有解释前不进入策略层。
