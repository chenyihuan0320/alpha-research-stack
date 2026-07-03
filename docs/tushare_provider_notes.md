# Tushare Provider Notes

## 使用目标

Tushare 在当前阶段只作为 A 股第二数据源，用于验证 AkShare 的日线、估值和基础财务字段覆盖。它不生成股票推荐、候选评分、回测结果、LLM 输出、日报或交易指令。

## Token 配置方式

真实 token 只允许通过环境变量传入：

```bash
export TUSHARE_TOKEN="..."
```

仓库只提交 `.env.example` 中的空占位：

```text
TUSHARE_TOKEN=
```

不要提交真实 token、API key、账号密码、Cookie 或任何私有凭证。

当前 adapter 直接使用 `ts.pro_api(token)` 初始化客户端，不调用 `ts.set_token(token)`，避免 Tushare 在 `$HOME/tk.csv` 写入 token 文件。

## A 股 Ticker Mapping

| 项目 ticker | Tushare ts_code | 说明 |
| --- | --- | --- |
| `600519.SH` | `600519.SH` | 上交所 |
| `000001.SZ` | `000001.SZ` | 深交所 |
| `300750.SZ` | `300750.SZ` | 深交所创业板 |

当前 adapter 只接受 `SH` / `SZ` 后缀。港股和美股 ticker 会抛出 `TushareProviderError`，避免误用。

## 计划验证字段

### daily_bar

- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `adjustment`

注意：Tushare `daily` 默认不是复权行情，当前 adapter 记录 `adjustment=none`，并标记 `adjustment_unverified:none`。如果后续使用复权因子，需要单独验证 `adj_factor` 口径。

### valuation_snapshot

- `date`
- `market_cap`
- `pe`
- `pb`
- `ps`
- `dividend_yield`

`ev_ebitda` 和 `fcf_yield` 当前不假设 Tushare daily_basic 直接可用。若真实 probe 返回这些字段，再更新映射和质量说明。

### fundamentals_snapshot

- `period_end`
- `report_date`
- `revenue`
- `gross_profit`
- `operating_income`
- `net_income`
- `operating_cash_flow`
- `free_cash_flow`
- `total_assets`
- `total_liabilities`
- `total_equity`
- `debt`
- `shares_outstanding`

当前财务字段映射是保守框架，计划从 `income`、`cashflow`、`balancesheet` 三类报表接口合并最新同一 `end_date` 样本。未明确验证的字段保持缺失并打 quality flag，不能把利润率、每股指标或财务比率当作报表金额使用。真实字段和单位必须通过 `scripts/probe_tushare.py` 记录后再升级为可用于策略证据。

## 与 AkShare 的交叉验证目标

- 日线价格：`open`、`high`、`low`、`close`
- 日线成交：`volume`、`amount`、`turnover`
- 估值：`market_cap`、`pe`、`pb`、`ps`、`dividend_yield`

`fcf_yield` 暂不参与比较，直到自由现金流和 market cap 单位都经过验证。跨源字段冲突必须记录，不允许选择对策略结果有利的数据。

## 已知风险

- token、权限、积分和接口配额可能导致 `needs_credentials` 或 provider 失败。
- `daily_basic` 在当前 token 下存在较严格频率限制，adapter 采用按最新 `trade_date` 批量拉取后按 `ts_code` 过滤，减少逐 ticker 请求。
- 当前 token 可能没有 `income`、`cashflow`、`balancesheet` 等财报接口权限；此时 fundamentals probe 应记录 provider failure，不伪造财务字段。
- Tushare 限频可能导致间歇失败，真实接入前需要缓存和重试设计。
- Tushare 日线默认未复权，和 AkShare `qfq` 样本可能存在复权口径差异。
- Tushare 日期多为 `YYYYMMDD` 字符串，需要统一转换为契约 `date`。
- `vol`、`amount`、`total_mv` 等字段单位需要真实 probe 和文档交叉确认。
- `market_cap`、PE、PB、PS 的 TTM/静态口径可能与 AkShare/Eastmoney 不一致。
- 财务字段可能来自指标表而不是原始三大表，口径需要与巨潮或原始财报复核。

## 为什么 Tushare 也不能单独决定信号

Tushare 是结构化数据源，不是信号系统。它不能解决数据口径冲突、财务异常解释、行业比较、样本外验证、回测偏差、风险约束或人工复盘问题。所有字段必须经过 provider probe、cross-source comparison 和 data_quality_gate 后，才能作为 provider evidence 进入后续候选发现层。

## 无 Token 时的 Expected Behavior

没有 `TUSHARE_TOKEN` 时：

- `scripts/probe_tushare.py` 生成 `outputs/reports/tushare_probe_report.md`。
- CN capability 状态为 `needs_credentials`。
- `scripts/compare_akshare_tushare.py` 生成 `outputs/reports/akshare_tushare_comparison.md`。
- comparison 状态为 `pending_credentials`。
- 脚本不崩溃，不伪造成功结果，不联网获取 Tushare 数据。

## 本次真实 Probe 记录

- Tushare 安装状态：已安装。
- Tushare 版本：`1.4.29`。
- token 状态：通过临时环境变量传入；未写入仓库文件或 `.env`。
- 日线接口：`daily` 对 `600519.SH`、`000001.SZ`、`300750.SZ` 返回成功。
- 日线字段：覆盖 `date`、`open`、`high`、`low`、`close`、`volume`、`amount`、`adjustment`，缺 `turnover`。
- 单位处理：`vol` 标准化为股，`amount` 标准化为元；仍保留 `unit_unverified`，待文档和更多样本确认。
- 估值接口：`daily_basic` 当前触发 `1次/小时` 或 `1次/分钟` 限频，估值 cross-source comparison 暂未完成。
- 财务接口：当前 token 无 `income` 访问权限，财务快照不可用。
- 交叉验证：AkShare 与 Tushare 日线在共同日期和不复权口径下，对 `open/high/low/close/volume/amount` 的差异为 0%，但因估值 provider failure 和单位未完全确认，`data_quality_gate=block`，不允许进入候选发现层。
