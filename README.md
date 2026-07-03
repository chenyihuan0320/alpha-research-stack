# Alpha Research Stack

Alpha Research Stack 是一个面向每日 A 股、港股、美股多空研究与信号生成的研究系统。项目重点不是覆盖尽可能多的股票，而是通过数据、研究、回测、复盘和报告闭环，提高少量高置信信号的准确率和可解释性。

## 项目目标

- 每日发现值得进一步研究的多头和空头候选。
- 对候选标的进行基本面、市场行为、新闻事件、行业比较和反证研究。
- 通过历史回测、样本外验证和信号复盘约束最终信号质量。
- 输出可追溯的研究报告、信号依据、风险条件和事后表现。
- 建立可复用、可审计、可持续迭代的研究基础设施。

## 非目标

- 不自动下单。
- 不连接券商交易接口执行交易。
- 不构成投资建议。
- 不承诺收益率、胜率或回撤控制。
- 不把 LLM 的主观判断直接当作最终 signal confidence。

## 开发方式

本项目采用 Codex CLI goal 驱动开发：

- 每次开发先明确目标、边界和验收条件。
- 开始修改前先阅读 [docs/progress.md](docs/progress.md)，确认当前状态和下一步。
- 每次变更保持小步、可审计、可回滚。
- 文档、架构、测试和实现需要同步演进。
- 完成修改后运行与变更相关的测试或检查；没有业务代码变更时至少说明测试不适用并运行必要的仓库检查。

## 复用优先原则

系统应优先复用成熟开源项目、数据源 SDK、回测框架、因子分析工具和金融研究框架，避免从零编写只能演示概念的 demo。

优先复用的方向包括：

- 数据获取与标准化：AkShare、Tushare、OpenBB、EdgarTools 等。
- 量化研究与回测：Qlib、vectorbt、Alphalens 等。
- 智能体研究框架：TradingAgents、FinRobot、FinGPT 等。
- 股票分析样例系统：AlphaSift、AlphaEvo、daily_stock_analysis 等。

自建模块只应出现在项目差异化明显、开源项目无法满足要求，或需要统一编排、审计、复盘和信号治理的地方。

## GitHub 协作流程

- 每个 Goal 使用一个独立分支。
- 每个 Goal 对应一个 PR，PR 中说明目标、主要改动、验收命令、测试结果和风险。
- 本地完成修改后运行 `make check`。
- push 后由 GitHub Actions 自动运行项目检查。
- 将 PR 或仓库链接发给 ChatGPT 审查，重点检查项目边界、进度文档、测试结果和潜在风险。

## 当前数据层路线

- 先定义统一数据契约，明确字段、来源、更新时间、质量标记和跨源校验边界。
- 再运行 provider probe，验证 AkShare、Tushare、EdgarTools、OpenBB 等 provider 的字段覆盖、凭证要求、ticker mapping 和失败风险。
- 再接真实数据源，且每个 provider 接入都必须留下字段覆盖和数据质量记录。
- 真实 provider 接入前不开发信号策略、候选评分、回测、LLM 日报或自动交易逻辑。

## 如何运行 AkShare Provider Probe

```bash
python -m pip install -e ".[dev,akshare]"
python scripts/diagnose_akshare_daily.py
python scripts/probe_akshare.py
```

该命令会联网访问 AkShare 上游数据源，只用于 provider validation。它不生成股票推荐、候选评分、回测或交易指令。失败报告也有价值，因为它会记录依赖安装、网络、接口、字段覆盖或 provider 异常问题。

AkShare 的 A 股/港股日线默认使用新浪财经接口，配置为 `ARS_AKSHARE_DAILY_SOURCE_MODE=sina_first`。可选值包括 `sina_first`、`eastmoney_first`、`eastmoney_only`、`sina_only`。当前环境下 Eastmoney 日线链路不稳定，因此 Eastmoney 只作为 fallback 和诊断路径。

Eastmoney 诊断仍可通过 `ARS_AKSHARE_EASTMONEY_PROXY_MODE` 设置 `auto`、`respect_env_proxy` 或 `direct_no_proxy`；默认 `auto` 会先尊重当前环境代理，失败后再尝试直连。报告会记录 configured/effective proxy mode、`NO_PROXY` 和当前可见代理变量，便于比较代理与直连模式的差异。

## 当前阶段

已完成开源审计、数据契约和 dry-run provider probe。当前 AkShare 最小 provider 已改为新浪日线优先、Eastmoney 诊断/fallback，并已通过 A 股/港股日线和 A 股估值最小样本验证；下一步是接入 Tushare 做 A 股交叉验证。
