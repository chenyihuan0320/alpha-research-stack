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
- 当前结论：已完成 ProviderEvidence -> AlphaSift adapter 输入边界和本地 AlphaSift 静态复用验证；尚未执行 AlphaSift runtime，不生成候选。
- 不自建原因：AlphaSift 已覆盖 YAML strategy、全市场筛选、run 保存和 T+N evaluation 的候选发现核心形态。
- Reuse Gate 边界：AlphaSift 不直接消费 provider 原始数据，只消费 `allowed_downstream` 包含 `alphasift` 或 `alphasift_exploratory` 的 ProviderEvidence。
- 后续验证：安装或运行本地 AlphaSift 后，执行 no-LLM quickstart / screen，并把真实输出保存为 `CandidateEvidence`。

#### AlphaSift 复用验证记录

- 已评估项目：AlphaSift。
- 验证日期：2026-07-04。
- 验证方式：读取 `outputs/evidence/provider_evidence.jsonl`，筛选 CN `daily_bar` 且 `allowed_downstream` 包含 `alphasift_exploratory` 的 evidence；静态检查本地 `references/alphasift` 的 README、`pyproject.toml` 和 CLI。
- 输入/输出契约：输入为 `ProviderEvidence` / `ProviderEvidence.to_dict()`；输出目标为 `CandidateEvidence`，但本次未产生真实候选输出。
- 数据质量门禁：只允许 `daily_bar` evidence 进入 AlphaSift adapter；`valuation` / `fundamentals` block 不得进入。
- 可复用模块：AlphaSift 的 CLI、`screen --no-llm` 路径、YAML strategy 机制、run 保存和 T+N evaluation 设计。
- 不能直接复用原因：本次未执行 runtime，尚未验证 AlphaSift 输入文件能由本项目 ProviderEvidence 直接生成；港股/美股支持仍需后续验证。
- 复用的设计：候选发现作为可审计 run；候选输出必须落为 `CandidateEvidence`，不能直接成为 signal。
- 自建范围如何最小化：本项目只维护 adapter、CandidateEvidence 契约和 ledger，不自建筛选器。
- 后续验证任务：在隔离环境运行 `alphasift screen <strategy> --no-llm`，确认真实输出字段和 `CandidateEvidence` 映射。

### 轻量验证

- 已评估项目：vectorbt。
- 当前结论：先做 adapter skeleton；只允许通过 gate 的 `daily_bar` 进入后续 vectorbt 验证。
- 不自建原因：vectorbt 已覆盖向量化持有期验证、交易成本、参数扫描和基础指标输出。
- Reuse Gate 边界：vectorbt 不直接消费 provider 原始数据，只消费 `allowed_downstream` 包含 `vectorbt` 的 ProviderEvidence。
- 后续验证：安装可选依赖后，用已验证 A 股日线样本跑最小事件持有期验证。

## 当前下一步

如果继续候选发现复用验证，下一步是在隔离环境中执行 AlphaSift no-LLM runtime，并把真实输出映射为 `CandidateEvidence`；如果暂不运行 AlphaSift，则可先做 vectorbt 最小事件验证，但仍只能消费 `allowed_downstream` 放行后的 ProviderEvidence。
