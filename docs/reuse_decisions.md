# Reuse Decisions

本文件是 Alpha Research Stack 的 Reuse Gate 记录。准备自建候选发现、回测、报告或 Agent 研究能力前，必须先验证对应开源项目是否可复用，并把结论写回本文件。

## Reuse Gate 原则

- 默认复用成熟开源项目，除非复用验证失败并记录原因。
- 不允许因为“自己实现更快”绕过复用验证。
- 复用验证必须先明确输入、输出、质量门禁、许可证、集成复杂度和失败替代方案。
- `data_quality_gate=block` 或 `pending_credentials` 的字段不能进入候选发现、回测验证、报告生成或 Agent 研究。
- Reuse Gate 依赖 Provider Evidence Ledger；下游组件只读取 `allowed_downstream` 放行后的 evidence。
- LLM ranking、第三方评分或示例策略输出不能直接成为最终 confidence。
- 自建代码只做编排、契约、适配、审计、证据链和校准，不重写通用框架。

## 核心能力优先复用项目

| 核心能力 | 优先复用项目 | 当前角色 |
| --- | --- | --- |
| 数据源 | AkShare / Tushare / EdgarTools / OpenBB | provider adapter 和字段覆盖验证 |
| 候选发现 | AlphaSift | YAML strategy、全市场筛选、candidate evidence 参考 |
| 轻量验证 | vectorbt | 事件/规则持有期验证、参数扫描 |
| 因子/模型研究 | Qlib | 因子研究、模型训练、组合验证 |
| 策略演化 | AlphaEvo | 第二阶段策略 DSL、变异、重测和抗过拟合参考 |
| 报告推送 | daily_stock_analysis | 报告模板、推送渠道、Web/API 工作台参考 |
| 多 Agent 深度研究 | TradingAgents / FinRobot | 多角色研究流程和报告结构参考 |

## 自建模块允许范围

- `orchestrator`
- provider adapters
- data contracts
- `data_quality_gate`
- evidence ledger
- signal ledger
- confidence calibration

这些模块必须尽量薄，只连接复用组件并保留数据质量、证据来源和复盘记录。

## 自建模块禁止范围

除非复用验证失败并记录原因，否则不允许自建：

- 全市场筛选器
- 完整回测框架
- 报告推送系统
- 多 Agent 投研系统
- 策略演化系统

## 复用决策记录模板

每次决定复用或自建时，至少记录：

- 已评估项目：
- 验证日期：
- 验证方式：
- 输入/输出契约：
- 数据质量门禁：
- 可直接复用模块：
- 不能直接复用原因：
- 复用的设计：
- 自建范围如何最小化：
- 后续验证任务：

## 当前决策

### 候选发现

- 已评估项目：AlphaSift。
- 当前结论：先做 adapter skeleton 和输入/输出契约；在 `data_quality_gate` 放行 provider evidence 前，不运行候选发现。
- 不自建原因：AlphaSift 已覆盖 YAML strategy、全市场筛选、run 保存和 T+N evaluation 的候选发现核心形态。
- Reuse Gate 边界：AlphaSift 不直接消费 provider 原始数据，只消费 `allowed_downstream` 包含 `alphasift` 或 `alphasift_exploratory` 的 ProviderEvidence。
- 后续验证：允许 clone/安装后运行 AlphaSift no-LLM quickstart，并把输出保存为 `candidate_evidence`。

### 轻量验证

- 已评估项目：vectorbt。
- 当前结论：先做 adapter skeleton；只允许通过 gate 的 `daily_bar` 进入后续 vectorbt 验证。
- 不自建原因：vectorbt 已覆盖向量化持有期验证、交易成本、参数扫描和基础指标输出。
- Reuse Gate 边界：vectorbt 不直接消费 provider 原始数据，只消费 `allowed_downstream` 包含 `vectorbt` 的 ProviderEvidence。
- 后续验证：安装可选依赖后，用已验证 A 股日线样本跑最小事件持有期验证。

## 当前下一步

必须先生成 Provider Evidence Ledger，把已验证 daily_bar 和被阻断 valuation / fundamentals 分开存储；再决定是否做 AlphaSift no-LLM 最小验证或 vectorbt 最小事件验证。
