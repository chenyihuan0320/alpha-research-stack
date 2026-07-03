# 开源项目选型审计

审计日期：2026-07-03

审计目标：为 Alpha Research Stack 的“每日 A 股、港股、美股高准确率多空研究与信号系统”选择可复用开源路径。结论只围绕高置信信号准确率、可验证性、可追溯性和集成成本，不以项目热度作为采用理由。

审计方法：读取 GitHub 仓库页面、README、license、目录结构、提交 Atom feed、PyPI JSON 元数据，以及仓库内已有 `references/` 只读参考代码。未 clone 外部项目，未安装依赖，未提交任何凭证。GitHub API 在本次审计中触发匿名限流，因此最近维护状态主要来自 GitHub commits Atom feed和 PyPI 上传时间；无法确认的信息明确标注“无法确认”。

## 推荐结论

### 1. 第一阶段推荐技术栈

- 数据层：
  - A 股：AkShare + Tushare 双源交叉验证。AkShare 覆盖广、无 token 门槛；Tushare Pro 更适合结构化财务、公司行动和基础信息，但需要 token/权限/积分治理。
  - 美股披露：EdgarTools。用于 10-K、10-Q、8-K、XBRL 财务报表、Form 4、13F 等结构化披露解析。
  - 美股/跨资产补充：OpenBB。作为美股行情、宏观、ETF、经济数据和统一 Python API 的补充入口，但 AGPL-3.0-only 许可证需要先做合规确认。
- 候选发现：
  - AlphaSift 作为 A 股全市场筛选和候选证据包的参考实现，优先复用其 YAML 策略、硬过滤、可审计 scoring、T+N evaluation loop 思路。
  - 第一阶段不直接复用 AlphaSift 的 LLM ranking 作为最终 confidence，只可作为研究辅助字段。
- 回测验证：
  - Qlib 用作中长期因子、模型、组合和回测研究底座。
  - vectorbt 用作快速事件策略、参数扫描和规则验证。
- 深度研究 / 报告推送：
  - daily_stock_analysis 作为多市场报告、新闻搜索、推送、Web/API 工作台参考。
  - TradingAgents 作为多角色研究辩论结构参考，但不采用其交易执行/Portfolio Manager 决策闭环。

### 2. 第二阶段推荐技术栈

- AlphaEvo：在第一阶段有稳定数据和回测基准后，再评估其策略 DSL、反思/变异/重测链路和抗过拟合约束。
- Alphalens：只在需要经典 factor tear sheet 时引入；由于维护停滞，应优先评估 Qlib 内置分析或自建轻量 IC/分层收益分析。
- FinRobot / FinGPT：作为金融 LLM/Agent 研究资料和文本处理参考，不进入第一阶段核心链路。

### 3. 不建议优先采用的项目及原因

- FinGPT：偏金融 LLM 模型与数据集，不直接解决多市场每日候选、回测、复盘和 confidence 校准。
- FinRobot：偏 LLM Agent 和 equity report demo，依赖外部 API key，适合作报告辅助，不适合作信号真实性来源。
- Alphalens：能力明确但维护状态老，现代 pandas/NumPy 兼容性和 A 股交易机制适配需要额外验证。
- TradingAgents 的“交易决策/下单模拟”模块：与本项目“不自动下单、不构成投资建议”的边界不匹配。
- OpenBB Workspace/企业 UI：可先不用；第一阶段只考虑 OpenBB Python/API 数据能力。

### 4. 需要自建的模块

- 多市场证券主数据、交易日历和代码映射。
- 数据质量审计、字段标准化、缺失值检查、来源优先级和数据血缘。
- 候选证据包格式：触发规则、数据版本、因子值、新闻/公告来源、风险标签。
- 最终 confidence 校准：必须由历史验证、样本外表现、信号复盘、规则稳定性、数据质量和人工可审计治理共同决定。
- 信号复盘数据库：记录发布时点、方向、confidence、持有期、收益、回撤、失败归因和 thesis 状态。
- 报告模板和推送策略：展示证据链，而不是只输出 LLM 观点。

### 5. 不能依赖开源项目解决的问题

- 高准确率本身：开源项目能提供数据、回测、研究框架，不能保证信号准确率。
- 最终 confidence：不能由 LLM、单一模型分数或第三方项目评分直接生成。
- 数据真实性和时效性：必须自建交叉验证、异常检测和数据版本记录。
- 过拟合控制：必须自建实验登记、样本切分、样本外验证和复盘制度。
- 合规边界：任何输出都不能变成自动交易指令或投资建议。

### 6. 下一步最小闭环路线

1. 建立数据层最小样本：A 股用 AkShare + Tushare，美股用 EdgarTools + OpenBB，港股先用 AkShare/OpenBB 验证覆盖。
2. 定义统一 `security_master`、`daily_bar`、`fundamentals`、`events`、`candidate_evidence`、`signal_review` 数据契约。
3. 选 2 个多头候选规则和 2 个空头候选规则，只用可解释数据，不接 LLM confidence。
4. 用 vectorbt 快速验证事件/规则持有期表现，用 Qlib 验证因子稳定性。
5. 用 daily_stock_analysis / TradingAgents 的报告结构做研究辅助输出，但最终 confidence 暂只来自验证层。
6. 连续复盘 20 个交易日后再决定是否引入 AlphaEvo 策略演化或 LLM ranking。

## 项目逐项审计

### 1. OpenBB-finance/OpenBB

- 项目定位：开放金融数据平台，面向分析师、量化和 AI agent，提供 Python、REST/API、MCP、Workspace/Excel 等消费方式。
- 仓库地址：https://github.com/OpenBB-finance/OpenBB
- license：AGPL-3.0-only。
- 最近维护状态：活跃；GitHub commits feed 显示 develop 分支 2026-06-25 更新，PyPI `openbb` 4.7.2 于 2026-05-26 上传，`openbb-cli` 1.4.2 于 2026-06-17 上传。
- 文档质量：高；README 链接官方文档、Python reference、CLI 文档和开发者文档。
- 是否可 pip install：是，`pip install openbb`；CLI 包为 `pip install openbb-cli`。
- 是否有 CLI：是，README 提到 `openbb-api` 和 OpenBB CLI。
- 是否有 Python API：是，示例为 `from openbb import obb`。
- 是否有 Docker / GitHub Actions：GitHub Actions 存在；Docker 支持未在 README 顶层明确确认。
- 是否支持 A股 / 港股 / 美股：美股是；A 股/港股依赖具体 provider，需最小验证。
- 是否支持行情：是。
- 是否支持财务报表：是，取决于 provider。
- 是否支持估值：是，取决于 provider。
- 是否支持新闻 / 情绪：部分支持，取决于 provider。
- 是否支持行业 / 竞争分析：部分支持数据，不提供本项目所需的研究判断。
- 是否支持全市场筛选：不作为核心能力。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：支持 MCP/AI agent 数据接口，但不是信号决策系统。
- 是否支持结构化输出：是，Python API 可转 DataFrame。
- 可复用模块：跨市场数据入口、Python API、REST/API、MCP server、宏观/ETF/美股数据 provider。
- 不建议复用模块：Workspace/企业 UI、任何直接替代本项目 signal confidence 的 agent 输出。
- 集成复杂度：中；主要风险是 provider 差异、认证、字段标准化和 AGPL 合规。
- 对“高准确率每日多空信号”的贡献评分：7/10。
- 推荐角色：数据层。
- 最小验证任务：验证 A 股、港股、美股各 20 只股票的日线、财务、估值、新闻字段覆盖；确认 AGPL 对本项目分发方式的影响。

### 2. microsoft/qlib

- 项目定位：AI-oriented quant investment platform，覆盖数据准备、模型训练、回测、组合分析、报告分析和自动 quant workflow。
- 仓库地址：https://github.com/microsoft/qlib
- license：MIT。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-04-22 更新，PyPI `pyqlib` 0.9.7 于 2025-08-15 上传。
- 文档质量：高；有 docs、examples、ReadTheDocs、benchmark config 和 CI workflow 说明。
- 是否可 pip install：是，`pip install pyqlib`。
- 是否有 CLI：是，`qrun`、`python -m qlib.cli.data`。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：是，README 提供 Docker image 用法，仓库有 GitHub Actions。
- 是否支持 A股 / 港股 / 美股：A 股和美股可用；港股需自备数据适配。
- 是否支持行情：是，需要准备 qlib 数据格式。
- 是否支持财务报表：否，非核心能力。
- 是否支持估值：否，需外部数据自建因子。
- 是否支持新闻 / 情绪：否，需外部数据。
- 是否支持行业 / 竞争分析：部分，取决于自备特征和分组。
- 是否支持全市场筛选：部分，可通过 universe、因子和模型预测实现。
- 是否支持回测：是。
- 是否支持因子验证：是，支持 IC、分组收益、组合分析等研究流程。
- 是否支持策略优化：是，模型和参数实验能力强；RD-Agent 是相邻项目，不应默认纳入第一阶段。
- 是否支持 LLM / Agent：Qlib 本体不是 LLM/Agent 框架；README 提到 RD-Agent 集成方向。
- 是否支持结构化输出：是。
- 可复用模块：数据格式、Alpha158/Alpha360 思路、workflow config、qrun、回测、风险/收益分析、模型 benchmark。
- 不建议复用模块：默认 Yahoo 数据下载作为高质量生产数据源；未经验证的自动 R&D agent。
- 集成复杂度：高；需要把 A/H/US 多市场数据标准化为 qlib 格式，并处理交易日历、停牌、涨跌停、幸存者偏差。
- 对“高准确率每日多空信号”的贡献评分：8/10。
- 推荐角色：回测验证 / 候选发现。
- 最小验证任务：用 300 只 A 股和 300 只美股构建 qlib 数据样本，跑 Alpha158 + LightGBM，输出 IC、分层收益和样本外结果。

### 3. ZhuLinsen/alphasift

- 项目定位：AI-native stock discovery and ranking engine，强调全市场发现、YAML 策略、可审计评分、可选 LLM ranking 和 T+N evaluation。
- 仓库地址：https://github.com/ZhuLinsen/alphasift
- license：Apache-2.0。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-07-01 更新。
- 文档质量：中高；README 给出 CLI、策略、hotspot、evaluation loop 和输出形态，但生态成熟度仍需验证。
- 是否可 pip install：不可确认 PyPI 包；README 支持 `pip install -e .`。
- 是否有 CLI：是，`alphasift strategies`、`alphasift screen`、`alphasift hotspots`、`alphasift audit`。
- 是否有 Python API：应有，仓库有 `alphasift` 包；公开 API 稳定性需验证。
- 是否有 Docker / GitHub Actions：GitHub Actions 存在；Docker 未确认。
- 是否支持 A股 / 港股 / 美股：A 股明确支持；港股/美股无法确认。
- 是否支持行情：是，A 股全市场 snapshot 和 K 线特征。
- 是否支持财务报表：部分，更多是筛选字段，不是完整财报解析。
- 是否支持估值：是，示例包含 PE/PB。
- 是否支持新闻 / 情绪：部分，支持 candidate context 和 hotspot；新闻源质量需验证。
- 是否支持行业 / 竞争分析：部分，支持热点/主题/leader stock。
- 是否支持全市场筛选：是，这是核心能力。
- 是否支持回测：不是完整回测；支持 T+N evaluation loop。
- 是否支持因子验证：部分，偏候选质量评估，不是系统性 factor tear sheet。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：是，可选 LLM ranking 和 agent-native `SKILL.md`。
- 是否支持结构化输出：是。
- 可复用模块：YAML 策略、硬过滤、候选打分、全市场筛选、hotspot discovery、run 保存和 T+N 评估。
- 不建议复用模块：LLM confidence 作为最终置信度；未经验证的数据抓取与排名权重。
- 集成复杂度：中。
- 对“高准确率每日多空信号”的贡献评分：8/10。
- 推荐角色：候选发现。
- 最小验证任务：用最近 60 个交易日 A 股快照复现 3 个策略，计算 T+1/T+5/T+20 收益、最大回撤、失败 breakout 标签稳定性。

### 4. ZhuLinsen/alphaevo

- 项目定位：self-evolving stock strategy research agent，用策略 DSL 做回测、诊断、变异、重测和证据追踪。
- 仓库地址：https://github.com/ZhuLinsen/alphaevo
- license：Apache-2.0。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-07-01 更新。
- 文档质量：中高；README 有 quick start、CLI 路径、架构、抗过拟合参数和 A 股/yfinance adapter 说明。
- 是否可 pip install：不可确认 PyPI 包；README 支持 `pip install -e .` 及 extras。
- 是否有 CLI：是，`alphaevo showcase`、`run`、`optimize`、`evolve`。
- 是否有 Python API：应有，仓库有 `src/alphaevo`；公开 API 稳定性需验证。
- 是否有 Docker / GitHub Actions：是，仓库有 Dockerfile 和 GitHub Actions。
- 是否支持 A股 / 港股 / 美股：A 股通过 AkShare extra，美股通过 yfinance；港股无法确认。
- 是否支持行情：是，依赖 yfinance/AkShare。
- 是否支持财务报表：否。
- 是否支持估值：否。
- 是否支持新闻 / 情绪：部分，美股可选 Adanos context；不是核心能力。
- 是否支持行业 / 竞争分析：否。
- 是否支持全市场筛选：否，偏策略研究。
- 是否支持回测：是。
- 是否支持因子验证：否。
- 是否支持策略优化：是，支持 objective、walk-forward/overfit gate 等参数。
- 是否支持 LLM / Agent：是，可选 LLM evolution。
- 是否支持结构化输出：是，报告和轨迹。
- 可复用模块：策略 DSL、回测评估、优化参数空间、抗过拟合 gate、证据链报告。
- 不建议复用模块：LLM 自动变异直接上线；未经过多市场真实数据验证的示例策略。
- 集成复杂度：中高。
- 对“高准确率每日多空信号”的贡献评分：7/10。
- 推荐角色：第二阶段回测验证 / 策略优化。
- 最小验证任务：在 Alpha Research Stack 自有数据上复现 2 个规则策略，比较 vectorbt/Qlib 结果，确认交易成本、样本切分和抗过拟合指标一致。

### 5. ZhuLinsen/daily_stock_analysis

- 项目定位：LLM 驱动多市场股票智能分析系统，覆盖行情、新闻、决策看板、Web/API、推送和自动化运行。
- 仓库地址：https://github.com/ZhuLinsen/daily_stock_analysis
- license：MIT。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-07-02 更新，本地参考仓库最近提交为 2026-07-02。
- 文档质量：高；README、完整指南、市场边界、数据源配置、通知配置较完整。
- 是否可 pip install：未发现 PyPI 包；以 requirements/本地运行为主。
- 是否有 CLI：是，`python main.py --stocks ...`、`--market-review`、`--schedule`、`--serve-only`。
- 是否有 Python API：是，仓库有 FastAPI `api/`、服务模块和 Python 包结构。
- 是否有 Docker / GitHub Actions：是，README 和目录均显示 Docker、GitHub Actions。
- 是否支持 A股 / 港股 / 美股：是，README 明确 A 股/港股/美股，还包括日/韩/台。
- 是否支持行情：是。
- 是否支持财务报表：部分支持，取决于市场和数据源。
- 是否支持估值：部分支持。
- 是否支持新闻 / 情绪：是，多搜索源和美股社交舆情可选。
- 是否支持行业 / 竞争分析：部分支持，偏报告辅助。
- 是否支持全市场筛选：否，主要面向自选股/输入列表。
- 是否支持回测：部分支持，仓库有 backtest API/页面，但不是核心验证框架。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：是。
- 是否支持结构化输出：是，报告、API schema、Markdown 和看板。
- 可复用模块：报告模板、推送渠道、新闻搜索聚合、多市场代码规范、Web/API 工作台、LLM 配置降级。
- 不建议复用模块：直接使用其买卖评分/看多看空作为 Alpha Research Stack 最终 confidence；GitHub Actions 中配置真实 secrets 的部署路径。
- 集成复杂度：中。
- 对“高准确率每日多空信号”的贡献评分：6.5/10。
- 推荐角色：深度研究 / 报告推送。
- 最小验证任务：把 Alpha Research Stack 候选证据包转成 DSA 可读输入，生成 10 份报告，人工检查事实引用、风险提示和结构化字段是否可复盘。

### 6. tauricresearch/tradingagents

- 项目定位：Multi-Agent LLM Financial Trading Framework，用基本面、情绪、新闻、技术、bull/bear researcher、risk manager 等角色模拟交易团队。
- 仓库地址：https://github.com/tauricresearch/tradingagents
- license：Apache-2.0。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-06-22 更新，本地参考仓库最近提交为 2026-06-22。
- 文档质量：中高；README 有架构、CLI、Docker、provider 和 release notes。
- 是否可 pip install：仓库支持 `pip install .`；PyPI `tradingagents` 当前指向其他 maintainer/repo，不能默认等同 tauricresearch 项目。
- 是否有 CLI：是，本地 pyproject 暴露 `tradingagents = "cli.main:app"`。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：是，README 提供 Docker compose；仓库有 GitHub Actions。
- 是否支持 A股 / 港股 / 美股：美股较明确；非美支持需验证；A 股/港股无法确认。
- 是否支持行情：是，依赖 yfinance 等 vendor。
- 是否支持财务报表：部分支持。
- 是否支持估值：部分支持。
- 是否支持新闻 / 情绪：是，新闻、Reddit、StockTwits、FRED、Polymarket 等。
- 是否支持行业 / 竞争分析：部分支持，通过 agent 推理完成。
- 是否支持全市场筛选：否。
- 是否支持回测：部分支持，但不是严谨因子/组合验证平台。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：是，核心能力。
- 是否支持结构化输出：是，README release notes 提到 structured-output agents。
- 可复用模块：多角色研究分工、bull/bear debate、risk review、结构化研究报告、checkpoint/decision log 思路。
- 不建议复用模块：交易执行、Portfolio Manager 直接 approve/reject、LLM 生成最终 confidence。
- 集成复杂度：中高；依赖多 LLM/data provider，输出稳定性需要约束。
- 对“高准确率每日多空信号”的贡献评分：5.5/10。
- 推荐角色：深度研究 / 报告推送。
- 最小验证任务：用同一批 20 个 AlphaSift 候选生成 bull/bear research，检查事实引用、反证质量、输出 schema 稳定性和幻觉率。

### 7. ai4finance-foundation/finrobot

- 项目定位：金融 LLM Agent 平台，偏 equity research assistant、multi-agent report、风险评估和金融自动化。
- 仓库地址：https://github.com/ai4finance-foundation/finrobot
- license：GitHub 仓库显示 Apache-2.0；PyPI metadata 显示 MIT，存在不一致，需合规确认。
- 最近维护状态：中等活跃；GitHub commits feed 显示 2026-05-10 更新，PyPI `FinRobot` 0.1.5 于 2024-06-17 上传。
- 文档质量：中；README 有 demo、config、部署说明，但生产化边界和数据质量控制需要验证。
- 是否可 pip install：是，PyPI 有 `FinRobot`，但版本较旧。
- 是否有 CLI：无法确认，主要是脚本和 Web app。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：Dockerfile 存在；GitHub Actions 未在目录列表中明确看到。
- 是否支持 A股 / 港股 / 美股：美股/英文 equity research 更明确；A 股/港股无法确认。
- 是否支持行情：部分，依赖外部 API。
- 是否支持财务报表：部分，依赖 FMP 等。
- 是否支持估值：部分。
- 是否支持新闻 / 情绪：部分。
- 是否支持行业 / 竞争分析：是，偏 LLM 报告。
- 是否支持全市场筛选：否。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：是，核心能力。
- 是否支持结构化输出：部分，需要验证 schema 稳定性。
- 可复用模块：报告 agent、equity research workflow、prompt/report 模板。
- 不建议复用模块：依赖 API key 的一键部署、LLM 投研结论作为信号、任何交易策略执行。
- 集成复杂度：高。
- 对“高准确率每日多空信号”的贡献评分：4.5/10。
- 推荐角色：第二阶段深度研究参考；第一阶段暂不采用。
- 最小验证任务：选 5 只美股生成 equity report，检查财务字段来源、引用、结构化输出和成本。

### 8. ai4finance-foundation/fingpt

- 项目定位：金融大语言模型、数据处理、训练/推理 notebook 和金融 NLP 任务集合。
- 仓库地址：https://github.com/ai4finance-foundation/fingpt
- license：MIT。
- 最近维护状态：活跃但偏研究；GitHub commits feed 显示 2026-06-01 更新，PyPI `FinGPT` 0.0.1 于 2023-10-20 上传。
- 文档质量：中；README 偏论文、模型、HuggingFace 和 notebook。
- 是否可 pip install：是，PyPI 有 `FinGPT`，但版本陈旧。
- 是否有 CLI：无法确认。
- 是否有 Python API：是，但生产 API 稳定性需验证。
- 是否有 Docker / GitHub Actions：GitHub Actions 存在；Docker 未确认。
- 是否支持 A股 / 港股 / 美股：不是市场数据工具，无法按市场直接支持。
- 是否支持行情：否。
- 是否支持财务报表：否。
- 是否支持估值：否。
- 是否支持新闻 / 情绪：是，偏金融 NLP/情绪模型。
- 是否支持行业 / 竞争分析：部分，依赖模型/prompt。
- 是否支持全市场筛选：否。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：是，金融 LLM 核心项目。
- 是否支持结构化输出：无法确认，需要二次封装。
- 可复用模块：金融情绪分析、金融文本数据处理、模型评估思路。
- 不建议复用模块：模型训练链路、大 notebook 直接进入生产、LLM 直接输出 signal confidence。
- 集成复杂度：高。
- 对“高准确率每日多空信号”的贡献评分：3/10。
- 推荐角色：暂不采用；作为金融 NLP 参考。
- 最小验证任务：只评估一个轻量情绪分类任务，比较与通用 LLM + 新闻源的增量价值。

### 9. polakowo/vectorbt

- 项目定位：向量化回测和策略研究引擎，强调大规模参数扫描、多资产回测、指标、组合分析和可视化。
- 仓库地址：https://github.com/polakowo/vectorbt
- license：Apache-2.0 with Commons Clause。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-06-29 更新，PyPI `vectorbt` 1.0.0 于 2026-04-22 上传。
- 文档质量：高；README、官网、示例、Docker images、Colab 均可用。
- 是否可 pip install：是，`pip install -U vectorbt`。
- 是否有 CLI：否，主要是 Python API。
- 是否有 Python API：是，核心能力。
- 是否有 Docker / GitHub Actions：Dockerfile、GitHub Actions 和 Docker images 均可见。
- 是否支持 A股 / 港股 / 美股：市场无关；取决于输入价格数据。内置示例偏 yfinance/美股/加密。
- 是否支持行情：内置数据访问有限；生产数据应由本项目数据层提供。
- 是否支持财务报表：否。
- 是否支持估值：否。
- 是否支持新闻 / 情绪：否。
- 是否支持行业 / 竞争分析：否。
- 是否支持全市场筛选：否。
- 是否支持回测：是，核心能力。
- 是否支持因子验证：部分，可做信号/组合分析，但不等同 Alphalens/Qlib factor tear sheet。
- 是否支持策略优化：是，参数扫描和组合实验强。
- 是否支持 LLM / Agent：不是 LLM 框架；README 提到可支持 AI agent-driven workflows，但需自建约束。
- 是否支持结构化输出：是。
- 可复用模块：事件规则回测、参数扫描、组合表现、交易/回撤/收益统计、Plotly 可视化。
- 不建议复用模块：内置数据源作为生产数据；商业限制未确认前的产品化分发。
- 集成复杂度：中。
- 对“高准确率每日多空信号”的贡献评分：8.5/10。
- 推荐角色：回测验证 / 策略优化。
- 最小验证任务：用本项目统一日线数据跑 4 个候选规则，输出 T+1/T+5/T+20、交易成本、行业中性后收益和参数敏感性。

### 10. quantopian/alphalens

- 项目定位：预测 alpha 因子的表现分析库，提供 returns analysis、IC analysis、turnover analysis、grouped analysis。
- 仓库地址：https://github.com/quantopian/alphalens
- license：Apache-2.0。
- 最近维护状态：维护停滞；GitHub commits feed 显示 2020-04-27 更新，PyPI `alphalens` 0.4.0 也为 2020-04-27 上传。
- 文档质量：中；经典文档和 notebook 示例足够，但生态老。
- 是否可 pip install：是，`pip install alphalens`。
- 是否有 CLI：否。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：GitHub Actions 目录存在；Docker 未确认。
- 是否支持 A股 / 港股 / 美股：市场无关，依赖输入 factor、pricing、groupby。
- 是否支持行情：否。
- 是否支持财务报表：否。
- 是否支持估值：否。
- 是否支持新闻 / 情绪：否。
- 是否支持行业 / 竞争分析：否。
- 是否支持全市场筛选：否。
- 是否支持回测：否，偏因子前向收益分析。
- 是否支持因子验证：是，核心能力。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：否。
- 是否支持结构化输出：是。
- 可复用模块：factor clean、forward returns、IC、分层收益、换手、group analysis。
- 不建议复用模块：作为第一阶段核心依赖；老版本直接绑定现代 pandas 环境。
- 集成复杂度：中。
- 对“高准确率每日多空信号”的贡献评分：6/10。
- 推荐角色：第二阶段回测验证参考。
- 最小验证任务：用一个 A 股估值因子和一个美股质量因子跑 tear sheet，确认 pandas 兼容性、行业分组和 A 股停牌/涨跌停处理。

### 11. dgunning/edgartools

- 项目定位：SEC EDGAR filings Python library，解析 10-K、10-Q、8-K、XBRL financials、Form 3/4/5、13F、ADV 等结构化披露。
- 仓库地址：https://github.com/dgunning/edgartools
- license：MIT。
- 最近维护状态：非常活跃；GitHub commits feed 显示 2026-06-29 更新，PyPI `edgartools` 5.40.1 于 2026-06-29 上传。
- 文档质量：高；README、docs、examples、notebooks、typed API、MCP/LLM-ready text 均明确。
- 是否可 pip install：是，`pip install edgartools`。
- 是否有 CLI：无法确认，核心是 Python API。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：GitHub Actions 存在；Docker 未确认。
- 是否支持 A股 / 港股 / 美股：美股 SEC 披露明确；A 股/港股不支持。
- 是否支持行情：否。
- 是否支持财务报表：是，美股披露强项。
- 是否支持估值：不直接支持，需要本项目计算。
- 是否支持新闻 / 情绪：否，支持 8-K 等事件披露，不是新闻情绪。
- 是否支持行业 / 竞争分析：部分，可通过公司披露文本和财务对比自建。
- 是否支持全市场筛选：部分，可按 SEC 公司/filings 批处理，但不是筛选引擎。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：部分，README 提到 MCP server 和 LLM-ready text。
- 是否支持结构化输出：是，typed objects、DataFrames、clean text。
- 可复用模块：美股财报解析、XBRL 标准化、insider trades、13F、8-K 事件、RAG 文本。
- 不建议复用模块：非美股数据；把披露文本摘要直接作为 confidence。
- 集成复杂度：低到中。
- 对“高准确率每日多空信号”的贡献评分：7.5/10。
- 推荐角色：数据层 / 深度研究。
- 最小验证任务：解析 30 家美股最近 10-K/10-Q，抽取收入、毛利、现金流、债务、股本变化，与 OpenBB/手工样本交叉验证。

### 12. akfamily/akshare

- 项目定位：Python 开源财经数据接口库，强调简单获取金融数据。
- 仓库地址：https://github.com/akfamily/akshare
- license：MIT。
- 最近维护状态：活跃；GitHub commits feed 显示 2026-05-27 更新，PyPI `akshare` 1.18.64 于 2026-05-27 上传。
- 文档质量：高；中文文档、Data Dict、Subjects、教程和示例完整。
- 是否可 pip install：是，`pip install akshare --upgrade`。
- 是否有 CLI：否，主要是 Python API。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：是，README 提供 Docker/Jupyter image，仓库有 GitHub Actions。
- 是否支持 A股 / 港股 / 美股：是；README 示例包含 A 股和美股，文档覆盖多市场，港股需按接口验证。
- 是否支持行情：是。
- 是否支持财务报表：是，按接口覆盖。
- 是否支持估值：是，按接口覆盖。
- 是否支持新闻 / 情绪：部分，按接口覆盖。
- 是否支持行业 / 竞争分析：部分，提供行业/主题/宏观数据，研究判断需自建。
- 是否支持全市场筛选：部分，可拉取全市场数据后自建筛选。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：否。
- 是否支持结构化输出：是，DataFrame。
- 可复用模块：A 股/港股/美股行情、A 股财务和估值、宏观、行业、主题、全市场快照。
- 不建议复用模块：直接信任单接口结果；无数据血缘和字段质量审计的裸调用。
- 集成复杂度：低到中。
- 对“高准确率每日多空信号”的贡献评分：8.5/10。
- 推荐角色：数据层 / 候选发现。
- 最小验证任务：固定 100 只 A 股、50 只港股、50 只美股，验证日线、复权、财务、估值、行业字段可用性和缺失率。

### 13. waditu/tushare

- 项目定位：中国股票历史和实时行情数据工具，Tushare Pro 提供更完整的 A 股结构化金融数据。
- 仓库地址：https://github.com/waditu/tushare
- license：BSD-3-Clause / BSD。
- 最近维护状态：代码仓库维护弱，但 PyPI 包仍更新；GitHub commits feed 显示 2020-03-04 更新，PyPI `tushare` 1.4.29 于 2026-03-25 上传。真实接口维护应以 https://tushare.pro 为准。
- 文档质量：中；GitHub README 老，Pro 官网文档需另行系统验证。
- 是否可 pip install：是，`pip install tushare`。
- 是否有 CLI：否。
- 是否有 Python API：是。
- 是否有 Docker / GitHub Actions：现代 GitHub Actions/Docker 未确认，仓库有旧 Travis。
- 是否支持 A股 / 港股 / 美股：A 股强；港股/美股不是核心。
- 是否支持行情：是。
- 是否支持财务报表：是，Pro 侧强。
- 是否支持估值：是。
- 是否支持新闻 / 情绪：部分，取决于 Pro 接口权限。
- 是否支持行业 / 竞争分析：部分，提供行业分类/基础数据，分析需自建。
- 是否支持全市场筛选：部分，可拉取全市场基础、行情和财务后自建。
- 是否支持回测：否。
- 是否支持因子验证：否。
- 是否支持策略优化：否。
- 是否支持 LLM / Agent：否。
- 是否支持结构化输出：是，DataFrame。
- 可复用模块：A 股基础信息、日线、复权、财务、估值、公司行动、交易日历。
- 不建议复用模块：依赖单一 token/积分接口作为唯一数据源；老 GitHub README 中的 legacy 接口。
- 集成复杂度：中；需要 token、权限、限频、缓存和字段版本治理。
- 对“高准确率每日多空信号”的贡献评分：7/10。
- 推荐角色：数据层。
- 最小验证任务：申请/配置测试 token 后，对 100 只 A 股拉取日线、财务、估值、交易日历，与 AkShare 逐字段对比。

## 来源索引

- OpenBB GitHub：https://github.com/OpenBB-finance/OpenBB；PyPI：https://pypi.org/project/openbb/；CLI PyPI：https://pypi.org/project/openbb-cli/
- Qlib GitHub：https://github.com/microsoft/qlib；PyPI：https://pypi.org/project/pyqlib/
- AlphaSift GitHub：https://github.com/ZhuLinsen/alphasift
- AlphaEvo GitHub：https://github.com/ZhuLinsen/alphaevo
- daily_stock_analysis GitHub：https://github.com/ZhuLinsen/daily_stock_analysis
- TradingAgents GitHub：https://github.com/tauricresearch/tradingagents
- FinRobot GitHub：https://github.com/ai4finance-foundation/finrobot；PyPI：https://pypi.org/project/FinRobot/
- FinGPT GitHub：https://github.com/ai4finance-foundation/fingpt；PyPI：https://pypi.org/project/FinGPT/
- vectorbt GitHub：https://github.com/polakowo/vectorbt；PyPI：https://pypi.org/project/vectorbt/
- Alphalens GitHub：https://github.com/quantopian/alphalens；PyPI：https://pypi.org/project/alphalens/
- EdgarTools GitHub：https://github.com/dgunning/edgartools；PyPI：https://pypi.org/project/edgartools/
- AkShare GitHub：https://github.com/akfamily/akshare；PyPI：https://pypi.org/project/akshare/
- Tushare GitHub：https://github.com/waditu/tushare；PyPI：https://pypi.org/project/tushare/；Pro 官网：https://tushare.pro
