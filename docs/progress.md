# 项目进度

## 2026-07-03

本次完成：

- 完成 AkShare 最小 provider 接入：`orchestrator/data/providers/akshare_provider.py`，支持 A 股 ticker、港股 ticker 映射，A 股日线、港股日线和 A 股估值样本函数。
- 完成 AkShare probe 脚本：`scripts/probe_akshare.py`，生成 `outputs/reports/akshare_probe_report.md`，记录 success / failed / skipped、字段覆盖、quality_flags 和失败原因。
- 完成 `docs/akshare_provider_notes.md`，记录 AkShare 使用目标、ticker mapping、接口名称、字段映射、风险和与 Tushare 交叉验证路径。
- 完成 CI/pytest 加固：`pyproject.toml` 增加 `dev = ["pytest>=8"]`，GitHub Actions 安装 `.[dev]` 后运行 `make check`，`scripts/dev_check.sh` 在检测到测试但没有 pytest 时会失败。
- 加强 provider probe 测试，并新增 AkShare ticker mapping 测试；测试不联网、不调用真实 AkShare。

本次未做：

- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 根据 AkShare probe 结果决定是否接入 Tushare 做 A 股交叉验证。

## 2026-07-03

本次完成：

- 完成 `docs/data_contract.md`，定义 `security_master`、`daily_bar`、`fundamentals_snapshot`、`valuation_snapshot`、`event_record`、`candidate_evidence` 的最小数据契约。
- 完成 `docs/provider_probe_plan.md`，记录 AkShare、Tushare、EdgarTools、OpenBB 和港股覆盖验证计划、ticker mapping 风险、凭证要求和替代方案。
- 完成 dry-run provider probe 框架：`orchestrator/data/contracts.py`、`sample_universe.py`、`provider_probe.py` 和 `scripts/probe_data_sources.py`。
- 完成 sample universe：`orchestrator/sample_data/universe_sample.csv`，覆盖 A 股、港股、美股共 9 个 ticker。
- 完成基础测试：数据契约转 dict、sample universe 加载/校验、CN/HK/US provider probe 计划。
- 确认 `scripts/dev_check.sh` 已使用 `exec > >(tee "${REPORT_FILE}") 2>&1`，避免 pytest 失败状态在管道子 shell 中丢失。

本次未做：

- 未联网。
- 未安装依赖。
- 未接真实 provider。
- 未实现股票推荐、候选评分、回测、LLM、日报或自动交易逻辑。

下一步：

- 真实接入 AkShare 作为第一个 provider，验证 A 股/港股日线和估值字段。

## 2026-07-03

本次完成：

- 修复 `scripts/dev_check.sh` 的 pytest 失败状态传播隐患：将报告输出改为 `exec > >(tee "${REPORT_FILE}") 2>&1`，避免报告生成管道左侧 subshell 吞掉 `PYTEST_STATUS`。
- 保持 `make check` 的终端输出和 `outputs/dev_checks/latest.md` 报告生成行为不变。

本次未做：

- 未实现业务代码。
- 未安装依赖。

下一步：

- 建立数据层最小样本和统一数据契约，启动 AkShare + Tushare + EdgarTools + OpenBB 的最小闭环验证。

## 2026-07-03

本次完成：

- 对 13 个候选开源项目完成真实选型审计：OpenBB、Qlib、AlphaSift、AlphaEvo、daily_stock_analysis、TradingAgents、FinRobot、FinGPT、vectorbt、Alphalens、EdgarTools、AkShare、Tushare。
- 更新 `docs/open_source_stack_audit.md`，加入推荐结论、阶段技术栈、不建议优先采用项目、需要自建模块、不能依赖开源解决的问题和下一步最小闭环路线。
- 按项目记录定位、仓库、license、维护状态、文档质量、安装方式、CLI/Python API/Docker/GitHub Actions、市场与能力覆盖、可复用模块、集成复杂度、贡献评分、推荐角色和最小验证任务。
- 联网读取 GitHub 页面、README、license/目录信息、commits Atom feed 和 PyPI JSON；未 clone 外部项目，未安装依赖，未提交凭证。

本次未做：

- 未实现业务代码。
- 未安装大型依赖。
- 未把外部项目 clone 到仓库。

下一步：

- 建立数据层最小样本和统一数据契约，启动 AkShare + Tushare + EdgarTools + OpenBB 的最小闭环验证。

## 2026-07-03

本次完成：

- 完成自动化检查脚本 `scripts/dev_check.sh`，生成 `outputs/dev_checks/latest.md` 并同步打印检查报告。
- 完成 `Makefile`，提供 `make check`、`make status`、`make progress` 和 `make tree`。
- 完成 GitHub Actions CI，在 push 和 pull_request 时运行项目检查。
- 完成 PR 模板和 Issue Goal 模板，固定 Goal 协作与审查信息。
- 更新 `README.md`、`AGENTS.md` 和 `.gitignore`，补充 GitHub 协作流程、Goal 完成规则和检查报告忽略规则。

本次未做：

- 未实现业务代码。
- 未做开源项目审计。
- 未安装依赖。

下一步：

- 开源项目选型审计。

## 2026-07-03

本次完成：

- 更新 `README.md`，明确 Alpha Research Stack 的项目目标、非目标、Codex CLI goal 驱动开发方式和复用优先原则。
- 更新 `AGENTS.md`，建立 Codex 开发规则、安全规则、开源复用优先原则和 LLM 使用边界。
- 创建 `docs/architecture.md`，定义总体架构、数据层、候选发现层、深度研究层、回测验证层、信号复盘层和报告推送层。
- 创建 `docs/open_source_stack_audit.md`，放置开源项目选型审计模板，覆盖 OpenBB、Qlib、AlphaSift、AlphaEvo、daily_stock_analysis、TradingAgents、FinRobot、FinGPT、vectorbt、Alphalens、EdgarTools、AkShare、Tushare。

本次未做：

- 未实现业务代码。
- 未联网审计开源项目。
- 未安装依赖。

下一步：

- 开源项目选型审计。
