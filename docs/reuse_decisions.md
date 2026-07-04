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

#### AlphaSift runtime 验证记录

- runtime 验证日期：2026-07-04。
- runtime 验证方式：从 ProviderEvidence 生成 `universe.csv`、`provider_evidence_mapping.json` 和最小 strategy YAML，在 `outputs/alphasift_runtime/` 下调用本地 `references/alphasift` 的 `alphasift.cli screen ... --no-llm`。
- 成功/失败状态：失败，`runtime_status=dependency_missing`。
- 失败原因：当前项目 venv 缺少 AlphaSift runtime 依赖 `yaml` / PyYAML，CLI 尚未启动到筛选阶段。
- 是否可直接复用：暂不能直接复用。
- 不能直接复用原因：依赖环境未准备完成，且尚未验证 AlphaSift runtime 能消费本项目生成的 ProviderEvidence 输入文件。
- 是否需要继续适配输入格式：需要。依赖补齐后还要验证 AlphaSift 输出是否能回连到 ProviderEvidence evidence_id。
- 是否仍禁止自建候选发现器：是。当前只是复用验证被依赖缺失阻断，不构成自建筛选器的理由。

### Candidate Engine Benchmark

验证日期：2026-07-04。

本次新增 Candidate Engine Benchmark，把候选发现从“绑定 AlphaSift”改为“多引擎候选证据统一接口”。AlphaSift 仍优先验证，但不再默认作为唯一候选发现主干。

当前角色边界：

- AlphaSift：`candidate_engine_candidate`，状态为 `pending_runtime`。适合轻量候选发现和 YAML strategy 验证，但 runtime 仍被依赖缺失阻断。
- Qlib：`factor_model_research_backbone`，当前状态为 `blocked_by_panel_data`。用于长期因子 / 模型研究主干，但当前 ProviderEvidence 只有 summary，不是 Qlib-ready panel。
- vectorbt：`validation_baseline`，状态为 `ready`。只做事件/规则验证 baseline，不是 candidate discovery 主引擎。
- OpenBB / EdgarTools：research / data input，只提供数据和研究输入，不作为 candidate generator。
- TradingAgents / FinRobot：deep research / report structure 参考，不是 signal source。

统一规则：

- 所有 candidate engine 输出必须映射为 `CandidateEvidence`。
- 任何 engine score 都不能直接成为最终 confidence。
- Benchmark 只评估 readiness，不运行 AlphaSift、Qlib 或 vectorbt，不生成候选。
- 如果选择自建候选发现器，必须先证明上述候选引擎不能满足最小复用路径，并记录失败原因。

#### Qlib data format feasibility 记录

- 验证日期：2026-07-04。
- 输入数据：`outputs/evidence/provider_evidence.jsonl` 中 CN `daily_bar` ProviderEvidence，共 3 条 eligible evidence。
- 当前是否 Qlib-ready：否，`qlib_runtime_ready=no`。
- 当前状态：`partial`。必需字段 `date,ticker,open,high,low,close,volume` 在字段语义层面可识别，但没有完整 `daily_bars` 时间序列 panel。
- 缺什么字段/格式：缺 Qlib-compatible 多日期 panel、特征/标签生成规则、Dataset Builder、以及 runtime 读取验证。
- 是否值得继续引入 Qlib：值得。Qlib 的长期价值在因子 / 模型研究、数据集管理和系统化验证，不应被短期 summary-only evidence 阻断。
- 为什么 Qlib 是长期主干而不是短期候选器：Qlib 需要稳定、宽表/长表 panel 和严格实验配置；短期应先构建 verified daily_bar panel，再做 minimal runtime validation，不应直接拿 ProviderEvidence summary 训练或筛选。

#### Verified DailyBarPanel 记录

- 验证日期：2026-07-04。
- 输入数据：`outputs/evidence/provider_evidence.jsonl` 中 `allowed_downstream` 放行的 CN `daily_bar` ProviderEvidence。
- 输出目标：`outputs/panels/cn_daily_bar_panel.csv` 和 `outputs/reports/verified_daily_bar_panel.md`。
- 当前角色：DailyBarPanel 是 Qlib / vectorbt 后续 runtime validation 的 dataset artifact；ProviderEvidence 仍是准入账本和溯源账本。
- 关键约束：不能用 summary evidence 伪造 daily_bars；每行 panel 必须保留 `provider_evidence_id`、`provider`、`cross_source_status`、`quality_flags` 和 `adjustment`。
- 当前 Qlib 含义：如果 panel 满足多 ticker、多日期和 `date,ticker,open,high,low,close,volume` 字段，只能把 Qlib 状态推进到 `ready_for_runtime_validation`；仍未运行 Qlib，也未训练模型。
- 后续验证任务：在不训练模型的前提下做 Qlib minimal runtime read validation，或先用 vectorbt 做事件验证 baseline。

### 轻量验证

- 已评估项目：vectorbt。
- 当前结论：先做 adapter skeleton；只允许通过 gate 的 `daily_bar` 进入后续 vectorbt 验证。
- 不自建原因：vectorbt 已覆盖向量化持有期验证、交易成本、参数扫描和基础指标输出。
- Reuse Gate 边界：vectorbt 不直接消费 provider 原始数据，只消费 `allowed_downstream` 包含 `vectorbt` 的 ProviderEvidence。
- 后续验证：安装可选依赖后，用已验证 A 股日线样本跑最小事件持有期验证。

## 当前下一步

根据 Candidate Engine Benchmark 和 Qlib feasibility，下一步三选一：基于 DailyBarPanel 做 Qlib minimal runtime read validation；补齐 AlphaSift runtime 依赖继续 no-LLM 验证；或先做 vectorbt event validation baseline。无论选择哪条路径，都只能消费 `allowed_downstream` 放行后的 ProviderEvidence 或由它生成并可回溯的 DailyBarPanel。
