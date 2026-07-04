# vectorbt Reuse Plan

## 目标角色

vectorbt 的目标角色是轻量事件/规则验证。它只提供历史验证证据，不生成最终 confidence，不替代信号治理，也不处理数据源质量问题。

## 为什么不自建回测框架

vectorbt 已经提供向量化验证、交易成本建模、参数扫描和常用表现指标。自建完整回测框架会把项目重心从证据链和质量治理转移到通用基础设施复刻。Alpha Research Stack 当前只需要先验证事件或规则在历史 daily_bar 上的表现，不需要生产级回测引擎。

## 需要验证的能力

- 用标准 `daily_bar` DataFrame 跑简单事件持有期验证。
- 交易成本。
- 参数扫描。
- 输出收益、回撤、胜率、MFE/MAE 或替代指标。

## 与 data_quality_gate 的关系

- 只有通过 gate 的 `daily_bar` 才能进入 vectorbt。
- `block` / `pending_credentials` 的数据不能进入验证。
- `warn` 数据可以进入探索性验证，但 warning 必须保留在结果中。
- valuation / fundamental 字段当前不能参与验证，因为 Tushare 估值限频、财务权限不足，且质量门禁仍阻断。

## 最小验证任务

当前先做 adapter skeleton：

- `VectorBTValidationInput`
- `VectorBTValidationResult`
- `can_send_to_vectorbt`
- `build_vectorbt_input`
- `parse_vectorbt_result`

后续安装 vectorbt 可选依赖后：

- 用通过 gate 的 A 股 daily_bar 样本构造 DataFrame。
- 跑一个无策略含义的事件持有期验证样例。
- 记录交易成本参数和样本窗口。
- 输出结构化 metrics，并作为 validation evidence 保存。

## 风险

- vectorbt 不是数据源。
- vectorbt 不处理数据口径、复权、单位、缺失、停牌和幸存者偏差问题。
- vectorbt 不能生成最终 confidence，只能提供历史验证证据。
- 生产级组合回测、跨市场日历和交易约束仍需后续评估 Qlib 或其他成熟框架。
