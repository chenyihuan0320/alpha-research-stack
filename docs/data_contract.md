# 数据层最小契约

本文件定义 Alpha Research Stack 的第一版数据层契约。当前阶段只定义字段、语义、质量边界和 JSON schema 风格结构，不实现数据库，也不接真实 provider。

数据契约先于策略开发，原因是：

- 多空信号准确率首先受数据覆盖、字段定义、复权口径、财报口径和时间戳影响。
- 没有统一契约时，策略很容易把 provider 特有字段当作稳定事实，导致回测和实盘复盘不一致。
- 候选发现、回测验证、深度研究和复盘都需要可追溯的数据来源、更新时间和质量标记。
- LLM 或 Agent 只能使用已经过契约约束的数据证据，不能绕过数据质量记录直接生成 confidence。

## 通用规则

- `market` 必须使用 `CN`、`HK`、`US`。
- `ticker` 使用项目内部标准 ticker，provider 专用格式必须在接入层转换。
- `source` 必须记录 provider 名称，例如 `akshare`、`tushare`、`edgartools`、`openbb`。
- `source_updated_at` 记录该 provider 返回数据或本地缓存刷新的时间。
- `quality_flags` 使用字符串列表记录缺失、冲突、估算、复权未知、币种不明等质量问题。
- 金额字段必须记录或可推导币种，不能混用人民币、港币和美元。
- 所有跨源校验字段都不能在冲突时静默覆盖，必须保留来源和差异。

## security_master

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| market | string | 是 | 否 | 是 | `CN` / `HK` / `US` |
| ticker | string | 是 | 否 | 是 | 项目内部标准 ticker |
| name | string | 是 | 否 | 是 | 证券名称 |
| exchange | string | 是 | 可空 | 是 | 交易所或板块 |
| currency | string | 是 | 可空 | 是 | CNY / HKD / USD |
| sector | string | 否 | 是 | 是 | 行业大类 |
| industry | string | 否 | 是 | 是 | 细分行业 |
| source | string | 是 | 否 | 否 | 数据来源 |
| source_updated_at | datetime | 是 | 否 | 否 | 来源更新时间 |
| is_active | boolean | 是 | 否 | 是 | 是否仍可交易或仍活跃 |
| notes | string | 否 | 是 | 否 | 备注 |

JSON schema 风格：

```json
{
  "market": "CN",
  "ticker": "600519.SH",
  "name": "Kweichow Moutai",
  "exchange": "SSE",
  "currency": "CNY",
  "sector": null,
  "industry": null,
  "source": "akshare",
  "source_updated_at": "2026-07-03T00:00:00Z",
  "is_active": true,
  "notes": null
}
```

## daily_bar

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| market | string | 是 | 否 | 是 | 市场 |
| ticker | string | 是 | 否 | 是 | 项目内部标准 ticker |
| date | date | 是 | 否 | 是 | 交易日 |
| open | number | 是 | 可空 | 是 | 开盘价 |
| high | number | 是 | 可空 | 是 | 最高价 |
| low | number | 是 | 可空 | 是 | 最低价 |
| close | number | 是 | 可空 | 是 | 收盘价 |
| adj_close | number | 否 | 是 | 是 | 复权收盘价 |
| volume | number | 是 | 可空 | 是 | 成交量 |
| amount | number | 否 | 是 | 是 | 成交额 |
| turnover | number | 否 | 是 | 是 | 换手率 |
| source | string | 是 | 否 | 否 | 数据来源 |
| source_updated_at | datetime | 是 | 否 | 否 | 来源更新时间 |
| adjustment | string | 是 | 可空 | 是 | `none` / `forward` / `backward` / `unknown` |
| quality_flags | array[string] | 是 | 否 | 否 | 质量标记 |

JSON schema 风格：

```json
{
  "market": "US",
  "ticker": "AAPL",
  "date": "2026-07-02",
  "open": 0.0,
  "high": 0.0,
  "low": 0.0,
  "close": 0.0,
  "adj_close": null,
  "volume": 0.0,
  "amount": null,
  "turnover": null,
  "source": "openbb",
  "source_updated_at": "2026-07-03T00:00:00Z",
  "adjustment": "unknown",
  "quality_flags": []
}
```

## fundamentals_snapshot

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| market | string | 是 | 否 | 是 | 市场 |
| ticker | string | 是 | 否 | 是 | ticker |
| period_end | date | 是 | 否 | 是 | 财报期末 |
| fiscal_period | string | 是 | 可空 | 是 | FY / Q1 / Q2 / Q3 / Q4 / TTM |
| report_date | date | 否 | 是 | 是 | 披露日期 |
| revenue | number | 否 | 是 | 是 | 收入 |
| gross_profit | number | 否 | 是 | 是 | 毛利 |
| operating_income | number | 否 | 是 | 是 | 营业利润 |
| net_income | number | 否 | 是 | 是 | 净利润 |
| operating_cash_flow | number | 否 | 是 | 是 | 经营现金流 |
| free_cash_flow | number | 否 | 是 | 是 | 自由现金流 |
| total_assets | number | 否 | 是 | 是 | 总资产 |
| total_liabilities | number | 否 | 是 | 是 | 总负债 |
| total_equity | number | 否 | 是 | 是 | 股东权益 |
| debt | number | 否 | 是 | 是 | 有息债务 |
| shares_outstanding | number | 否 | 是 | 是 | 股本或流通股口径需注明 |
| source | string | 是 | 否 | 否 | 数据来源 |
| source_updated_at | datetime | 是 | 否 | 否 | 来源更新时间 |
| quality_flags | array[string] | 是 | 否 | 否 | 质量标记 |

JSON schema 风格：

```json
{
  "market": "US",
  "ticker": "MSFT",
  "period_end": "2026-06-30",
  "fiscal_period": "FY",
  "report_date": null,
  "revenue": null,
  "gross_profit": null,
  "operating_income": null,
  "net_income": null,
  "operating_cash_flow": null,
  "free_cash_flow": null,
  "total_assets": null,
  "total_liabilities": null,
  "total_equity": null,
  "debt": null,
  "shares_outstanding": null,
  "source": "edgartools",
  "source_updated_at": "2026-07-03T00:00:00Z",
  "quality_flags": []
}
```

## valuation_snapshot

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| market | string | 是 | 否 | 是 | 市场 |
| ticker | string | 是 | 否 | 是 | ticker |
| date | date | 是 | 否 | 是 | 估值日期 |
| market_cap | number | 否 | 是 | 是 | 总市值 |
| pe | number | 否 | 是 | 是 | PE，需记录静态/TTM 来源口径 |
| pb | number | 否 | 是 | 是 | PB |
| ps | number | 否 | 是 | 是 | PS |
| ev_ebitda | number | 否 | 是 | 是 | EV/EBITDA |
| dividend_yield | number | 否 | 是 | 是 | 股息率 |
| fcf_yield | number | 否 | 是 | 是 | 自由现金流收益率 |
| source | string | 是 | 否 | 否 | 数据来源 |
| source_updated_at | datetime | 是 | 否 | 否 | 来源更新时间 |
| quality_flags | array[string] | 是 | 否 | 否 | 质量标记 |

JSON schema 风格：

```json
{
  "market": "CN",
  "ticker": "300750.SZ",
  "date": "2026-07-03",
  "market_cap": null,
  "pe": null,
  "pb": null,
  "ps": null,
  "ev_ebitda": null,
  "dividend_yield": null,
  "fcf_yield": null,
  "source": "akshare",
  "source_updated_at": "2026-07-03T00:00:00Z",
  "quality_flags": []
}
```

## event_record

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| market | string | 是 | 否 | 是 | 市场 |
| ticker | string | 是 | 否 | 是 | ticker |
| event_date | date | 是 | 否 | 是 | 事件日期 |
| event_type | string | 是 | 否 | 是 | earnings / filing / dividend / buyback / regulation / other |
| title | string | 是 | 否 | 是 | 标题 |
| summary | string | 否 | 是 | 否 | 摘要 |
| url | string | 否 | 是 | 否 | 来源链接 |
| source | string | 是 | 否 | 否 | 数据来源 |
| source_updated_at | datetime | 是 | 否 | 否 | 来源更新时间 |
| quality_flags | array[string] | 是 | 否 | 否 | 质量标记 |

JSON schema 风格：

```json
{
  "market": "US",
  "ticker": "NVDA",
  "event_date": "2026-07-03",
  "event_type": "filing",
  "title": "SEC filing",
  "summary": null,
  "url": null,
  "source": "edgartools",
  "source_updated_at": "2026-07-03T00:00:00Z",
  "quality_flags": []
}
```

## candidate_evidence

| 字段 | 类型 | 必须 | 可空 | 跨源校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| run_id | string | 是 | 否 | 否 | 候选发现运行 ID |
| market | string | 是 | 否 | 是 | 市场 |
| ticker | string | 是 | 否 | 是 | ticker |
| candidate_date | date | 是 | 否 | 是 | 候选日期 |
| source_strategy | string | 是 | 否 | 否 | 触发策略或规则名称 |
| evidence_type | string | 是 | 否 | 否 | price / valuation / fundamental / event / manual |
| evidence_payload | object | 是 | 否 | 否 | 结构化证据 |
| data_sources | array[string] | 是 | 否 | 否 | 使用的数据源 |
| quality_flags | array[string] | 是 | 否 | 否 | 质量标记 |
| created_at | datetime | 是 | 否 | 否 | 证据创建时间 |

JSON schema 风格：

```json
{
  "run_id": "dry-run-20260703",
  "market": "HK",
  "ticker": "0700.HK",
  "candidate_date": "2026-07-03",
  "source_strategy": "provider_probe",
  "evidence_type": "coverage",
  "evidence_payload": {"provider": "akshare", "capability": "daily_bar"},
  "data_sources": ["akshare"],
  "quality_flags": [],
  "created_at": "2026-07-03T00:00:00Z"
}
```

## 跨市场特殊注意点

### A 股

- ticker mapping 常见格式包括 `600519.SH`、`600519.SS`、`sh600519`，接入层必须统一到项目格式。
- 交易制度存在涨跌停、停牌、复权、除权除息、ST、退市整理等特殊情况。
- AkShare 和 Tushare 字段名、复权口径、财务报表发布日期可能不一致，必须交叉验证。
- Tushare 需要 token/积分/权限，真实 token 只能通过环境变量配置。

### 港股

- ticker mapping 常见格式包括 `0700.HK`、`00700.HK`、`700.HK`。
- 港币、人民币柜台、不同 provider 的成交额币种和单位需要校验。
- 港股财务和行业字段覆盖不稳定，第一阶段只验证日线覆盖，不作为强依赖。

### 美股

- ticker mapping 需要处理 share class、点号/连字符、退市 ticker 和并购变更。
- EdgarTools 提供 SEC 披露，不提供行情；OpenBB 或其他 provider 才能补行情和估值。
- 财报字段需要处理 GAAP/Non-GAAP、年度/季度/TTM、fiscal year 与 calendar year 差异。

## 必须先做 provider probe

任何真实 provider 接入前，必须先记录：

- provider 对每个契约字段的覆盖情况。
- 缺失率和字段单位。
- ticker mapping 是否稳定。
- 是否需要凭证、限频、缓存和许可证确认。
- 与第二来源的冲突字段和处理策略。
