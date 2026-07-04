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
