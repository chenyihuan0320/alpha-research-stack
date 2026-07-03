# 项目进度

## 2026-07-03

本次完成：

- 修复 A 股估值字段覆盖：`market_cap`、`pe`、`pb` 改为取 Baidu 估值序列的共同最新日期，避免三者日期不一致时静默合并。
- 补充 A 股估值字段：从东财估值比较原始 JSON 补充 `ps`，并在可用时补充 `ev_ebitda`；银行样本 `000001.SZ` 当前缺 `ev_ebitda`。
- 增加估算股息率：使用新浪分红明细近 365 日现金分红和最新日线 close 估算 `dividend_yield`，并标记 `estimated_value` 和单位/日期质量风险。
- 明确 `fcf_yield` 不硬填：当前 AkShare 估值 provider 没有可靠自由现金流口径，继续标记缺失，等待后续财务现金流字段验证后计算。
- 修复 provider 日期解析边界：`_to_date` 支持 `NaT`、`nan`、`--` 等 provider 空日期值，避免真实 probe 中分红明细解析崩溃。
- 重新运行真实 AkShare probe：主 probe 结果保持 `success=9`、`failed=0`、`skipped=3`；A 股估值覆盖率提升到 `600519.SH=87.5%`、`000001.SZ=75.0%`、`300750.SZ=87.5%`。
- 新增/更新不联网测试，覆盖共同日期合并、补充 `ps/ev_ebitda/dividend_yield`、银行样本缺 `EV/EBITDA` 时仍保留 `ps`、`NaT` 日期解析。

本次未做：

- 未接 Tushare。
- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 接入 Tushare 或交易所/财报源做 A 股估值和自由现金流交叉验证；在验证 `operating_cash_flow`、资本开支和 market cap 口径前，不计算生产级 `fcf_yield`。

## 2026-07-03

本次完成：

- 修复 AkShare/Eastmoney 日线 provider：在 AkShare Python requests 路径失败后，增加命令行 `curl` fallback，直接请求 Eastmoney kline JSON 并解析为同款日线字段。
- 增加 Eastmoney host fallback：A 股/港股日线会尝试默认 host 和少量 `*.push2his.eastmoney.com` 变体，并在报告中保留每个 proxy mode / transport 的失败摘要。
- 增加 AkShare/Sina 日线主路径：默认 `ARS_AKSHARE_DAILY_SOURCE_MODE=sina_first`，A 股使用 `stock_zh_a_daily`，港股使用 `stock_hk_daily`，Eastmoney 降为 fallback/诊断路径。
- 更新 `scripts/diagnose_akshare_daily.py`：区分 `akshare_requests` 与 `curl_cli` transport，记录单次诊断的 proxy mode、columns、shape 和失败原因。
- 更新 `scripts/probe_akshare.py` 报告摘要：`daily_bar_retry_mode_summary` 按 `proxy_mode/transport` 统计，避免把 requests 与 curl fallback 混在一起。
- 修复 `scripts/dev_check.sh` 的 pytest 发现逻辑：未激活 venv 时也可回退到 `.venv/bin/python -m pytest`，保证本地 `make check` 可直接运行。
- 重新运行真实 AkShare probe：当前环境 AkShare `1.18.64`，`daily_source_mode=sina_first`，主 probe 结果为 `success=9`、`failed=0`、`skipped=3`；A 股/港股日线和 A 股估值样本全部通过当前最小 universe。
- 单次 diagnostics 显示 `akshare_sina` 成功，Eastmoney requests/curl 仍可能返回 remote disconnect 或 `curl: (52) Empty reply from server`，说明稳定主路径应优先使用新浪接口。

本次未做：

- 未接 Tushare。
- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 保留 AkShare/Sina 作为第一阶段免费日线主路径；继续用 AkShare/Eastmoney 做对照诊断，并优先接 Tushare 做 A 股日线和估值交叉验证。

## 2026-07-03

本次完成：

- AkShare import 成功，版本为 `1.18.64`；A 股估值 probe 部分成功，当前覆盖 `market_cap`、`pe`、`pb`。
- AkShare 日线接口失败原因集中在 Eastmoney remote disconnect：`respect_env_proxy` 表现为 proxy remote disconnect，`direct_no_proxy` 表现为 remote disconnect。
- 新增 Eastmoney proxy mode 配置：`ARS_AKSHARE_EASTMONEY_PROXY_MODE=auto|respect_env_proxy|direct_no_proxy`，默认 `auto`，先尝试代理再尝试直连，并在失败 reason 中保留两种模式的摘要。
- 新增 `scripts/diagnose_akshare_daily.py`，生成 `outputs/reports/akshare_daily_diagnostics.md`，记录 Python executable、AkShare 版本、proxy env vars、接口返回 shape/columns、失败原因和 alternative daily function 候选。
- 修正估值合并质量：`stock_zh_valuation_baidu` 不再把不同日期的指标静默合成多条看似完整的快照；当前输出 latest merged snapshot，并用 `asof_mismatch` 和 `partial_coverage` 标记日期不一致和字段覆盖不足。
- 重新运行真实 diagnostics 和 probe：diagnostics 中 `respect_env_proxy` 和 `direct_no_proxy` 均失败；主 probe auto 模式出现少量日线间歇成功，但 Eastmoney 日线仍不能作为稳定数据源。

本次未做：

- 未接 Tushare。
- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 如果后续 diagnostics 显示 `respect_env_proxy` 稳定成功，则默认模式可改为 `respect_env_proxy` 或继续使用 `auto`。
- 如果后续 diagnostics 显示 `direct_no_proxy` 稳定成功，则保留 `direct_no_proxy` 或 `auto`。
- 如果两种模式仍失败，则 AkShare 日线暂时降级，转向 Tushare 或其他 provider 做日线验证。

## 2026-07-03

本次完成：

- 按验证要求将 AkShare Eastmoney 日线 probe 默认模式改回 `env_proxy`，沿用当前环境中的 `HTTP_PROXY` / `HTTPS_PROXY` 等代理变量。
- 将 A 股日线真实请求窗口限制为最近 180 天，避免为了 tail(5) 拉取全量历史。
- 修复 AkShare probe 报告成功项二次联网采样 raw keys 导致的状态污染，改为使用本次成功样本的标准化字段键名。
- 增加 probe retry：每个 capability 最多尝试 2 次，失败时记录最后一次异常和 attempts。
- 重新运行真实 AkShare probe：AkShare `1.18.64` 已安装；`eastmoney_proxy_mode` 为 `env_proxy`；A 股估值全部成功；最新报告中 `300750.SZ` A 股日线成功，`600519.SH`、`000001.SZ` 和三只港股日线仍出现 proxy remote disconnect，已固化失败原因。多轮 probe 显示 Eastmoney 日线成功 ticker 存在波动。

本次未做：

- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 保留 AkShare 作为可用但不稳定的数据源；优先接入 Tushare 做 A 股日线和估值交叉验证，并继续比较 Eastmoney 在代理与直连模式下的端点稳定性。

## 2026-07-03

本次完成：

- 完成 AkShare 可选依赖配置：`pyproject.toml` 增加 `akshare = ["akshare"]`，保留 `dev = ["pytest>=8"]`。
- 完成 AkShare 真实 provider probe 记录：本地安装 AkShare `1.18.64` 后运行 `scripts/probe_akshare.py`，生成 `outputs/reports/akshare_probe_report.md`。
- 完成 `daily_bar.adjustment` 契约修正，允许 `none`、`qfq`、`hfq`、`forward`、`backward`、`unknown`，并要求 adapter 记录 provider 原始复权参数。
- 完成字段映射和 quality_flags 修正：A 股估值接口调整为 `stock_zh_valuation_baidu`，新增/使用 `parse_error`、`unit_unverified`、`adjustment_unverified`、`provider_error`。
- 真实 probe 结果显示：A 股估值样本可用，A 股/港股日线在当前网络代理下请求 Eastmoney 端点失败，已记录失败原因。

本次未做：

- 未实现股票推荐。
- 未实现候选评分。
- 未实现回测。
- 未接 LLM。
- 未写日报。
- 未自动交易。
- 未提交任何 token、API key 或真实凭证。

下一步：

- 如果 AkShare A 股日线和估值字段可用，则接入 Tushare 做 A 股交叉验证；如果日线仍不可用，则先修复 AkShare provider 的网络/接口可用性问题。

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
