# AlphaSift Reuse Plan

## 目标角色

AlphaSift 的目标角色是候选发现层。它只负责从合格 provider evidence 中产生候选发现证据，不直接生成最终信号、最终 confidence 或投资建议。

## 为什么不自建候选发现器

AlphaSift 已经围绕候选发现提供了本项目需要先验证的关键形态：YAML strategy、硬过滤、全市场筛选、可审计评分、run 保存和 T+N evaluation loop。自建候选发现器会过早复制通用筛选能力，偏离 Alpha Research Stack 的核心：编排、质量门禁、证据链、复盘和 confidence calibration。

## 需要验证的能力

- YAML strategy
- universe 输入
- no-LLM screen
- candidate evidence 输出
- run 保存
- T+N evaluation

## 与当前数据层的关系

- `data_quality_gate=block` 时，不能把字段喂给 AlphaSift 做候选发现。
- `pending_credentials` 不是可用数据，不能被伪造成候选发现输入。
- 只能使用 `pass` / `warn` 且字段语义明确的数据作为 provider evidence。
- `warn` 字段必须带着质量标记进入 evidence，不允许静默变成干净字段。
- AlphaSift 输出必须保存为 `candidate_evidence`，不能直接变成信号。

## 最小验证任务

当前不安装或 clone 大型项目，先定义 adapter skeleton 和输入/输出格式：

- `AlphaSiftCandidateInput`
- `AlphaSiftCandidateOutput`
- `can_send_to_alphasift`
- `build_alphasift_input`
- `parse_alphasift_output`

后续如果允许 clone 或安装：

- 运行 AlphaSift quickstart。
- 运行 no-LLM screen。
- 使用最小 universe 验证输入字段需求。
- 确认输出能映射为 `candidate_evidence`。
- 验证 run 保存和 T+N evaluation 输出是否可复盘。

## 风险

- A 股支持明确，港股/美股需验证。
- LLM ranking 不能作为最终 confidence。
- AlphaSift 输出必须保存为 candidate evidence，而不是直接变成信号。
- 当前 data_quality_gate 仍会阻断估值和财务字段进入候选发现层。
- AlphaSift 自带数据源和本项目 provider evidence 之间的字段口径需要明确映射。

## Goal 009 验证结果

验证日期：2026-07-04

本次验证只做 AlphaSift no-LLM 最小复用边界验证，不执行筛选，不生成股票推荐，不生成最终 signal，不做 confidence、回测、LLM 或自动交易。

### 本地项目发现

- 已发现本地 AlphaSift 引用：`references/alphasift`。
- 已静态读取 README、`pyproject.toml` 和 CLI 入口。
- License 静态识别为 Apache-2.0。
- CLI console script 静态识别为 `alphasift = "alphasift.cli:main"`。
- README / CLI 中可见 `screen --no-llm` 路径。

### no-LLM 运行状态

- 本次未执行 AlphaSift runtime。
- 本次未安装 AlphaSift 依赖。
- 本次未 clone 外部项目。
- 本次未生成 `outputs/candidates/candidate_evidence.jsonl`。
- 当前验证状态：`local_project_inspected_runtime_not_executed`。

### 输入字段映射

`ProviderEvidence` 已可映射为 `AlphaSiftCandidateInput`：

- `run_id` -> AlphaSift run boundary。
- `market` / `ticker` -> universe / candidate key。
- `observed_at` 或 `source_updated_at` -> `candidate_date`。
- `gate_status` -> `quality_gate_status`。
- `ProviderEvidence.to_dict()` -> `provider_evidence`。

当前只允许：

- `data_domain=daily_bar`
- `allowed_downstream` 包含 `alphasift` 或 `alphasift_exploratory`

`valuation` / `fundamentals` block 证据必须拒绝。

### 输出映射状态

- 已建立 `CandidateEvidence` 数据模型和 JSONL ledger。
- 由于未执行 AlphaSift no-LLM，本次没有真实 AlphaSift 输出可映射。
- 后续只有在真实 AlphaSift 输出存在时，才允许写入 `CandidateEvidence`；不得用 mock candidate、ticker 排名或手写规则替代。

### 是否允许进入真实候选发现

当前不允许进入真实候选发现。

原因：

- AlphaSift runtime 未执行。
- AlphaSift 输入文件格式仍需用本项目 `ProviderEvidence` 做实际适配验证。
- 当前 validation 只证明本地项目具备静态 no-LLM 入口，不证明可直接消费本项目数据。

下一步：

- 在隔离环境中安装或运行本地 AlphaSift。
- 使用 `ProviderEvidence` 生成 AlphaSift 所需输入文件。
- 执行 `alphasift screen <strategy> --no-llm`。
- 将真实输出映射为 `CandidateEvidence`，仍不得生成最终信号或投资建议。

## Goal 010 runtime 验证结果

验证日期：2026-07-04

本次验证尝试在隔离输出目录中真实运行本地 AlphaSift no-LLM screen。运行脚本为 `scripts/run_alphasift_no_llm_validation.py`。

### 是否执行 runtime

- 已尝试执行 runtime。
- 使用本地 AlphaSift 路径：`references/alphasift`。
- 未 clone 外部项目。
- 未自动安装依赖。
- 未使用 LLM。

### 使用的命令

```bash
.venv/bin/python -m alphasift.cli screen ars_provider_evidence --market cn --max-output 3 --no-llm --no-post-analysis --no-daily-enrich --output outputs/alphasift_runtime/output/alphasift_screen.jsonl --jsonl
```

### 输入文件格式

已生成：

- `outputs/alphasift_runtime/input/universe.csv`
- `outputs/alphasift_runtime/input/provider_evidence_mapping.json`
- `outputs/alphasift_runtime/input/ars_provider_evidence.yaml`

这些文件只来自 `daily_bar` ProviderEvidence，不使用 `valuation` 或 `fundamentals` block 数据。

### runtime 结果

- `runtime_status`: `dependency_missing`
- `exit_code`: `1`
- 失败原因：当前项目 venv 无法导入 AlphaSift 依赖 `yaml`，报错为 `ModuleNotFoundError: No module named 'yaml'`。
- 未生成 AlphaSift JSONL 输出。
- 未写入 `outputs/candidates/candidate_evidence.jsonl`。

### CandidateEvidence 映射状态

- CandidateEvidence 映射代码已建立。
- 本次没有真实 AlphaSift pick 输出，因此没有可映射候选。
- 不允许用输入 ticker、adapter preview 或 mock payload 伪造 CandidateEvidence。

### 当前是否允许进入真实候选发现

当前不允许进入真实候选发现。

原因：

- AlphaSift runtime 尚未跑通。
- 依赖缺失阻断了 CLI 启动。
- 尚未验证 AlphaSift 输出能和本项目 ProviderEvidence 一一对应。

下一步：

- 在用户明确批准后，为隔离 AlphaSift runtime 环境安装最小依赖，例如 AlphaSift 自身 `pyproject.toml` 声明的运行依赖。
- 重新运行 `scripts/run_alphasift_no_llm_validation.py`。
- 只有真实 AlphaSift pick 输出可解析且能匹配 ProviderEvidence 时，才写入 CandidateEvidence。
