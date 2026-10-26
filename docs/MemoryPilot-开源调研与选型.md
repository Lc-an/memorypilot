# MemoryPilot 开源调研与选型

核对日期：2026-10-24（北京时间）

本文区分三件事：项目公开了什么、我们实际检查了什么、为本项目做了什么选择。维护记录、宣传分数和软件版本不等同于本项目实测结果。代码快照和软件包发布信息保存在同目录的 `research-snapshot.json`。

## 1. 选型结论

主线：**LangGraph 官方 ReAct 模板 + LangMem + PostgreSQL/pgvector + Qwen3 文本检索 + Streamlit**。

评测：**LongMemEval cleaned 为记忆主评测，MemoryArena 行程规划为后期任务评测，中文自建案例为产品回归**。

现成系统对照：先 Mem0，再按剩余时间增加 Hindsight。

观察和报告：第一版结构化日志即可；需要可视化比较时再增加 Langfuse 或 Promptfoo。主应用不依赖任何收费托管控制台。

这个选择使大部分基础设施已有实现，你的工作集中在时间版本、来源、信息选择与评测控制。

## 2. 候选比较

| 候选 | 已核对的能力与状态 | 决定 |
|---|---|---|
| [react-agent](https://github.com/langchain-ai/react-agent) | 现成模型与工具循环、配置与测试目录；MIT | 作为主仓库，保留上游结构 |
| [LangMem](https://github.com/langchain-ai/langmem) | 结构化抽取、记忆管理和摘要；MIT | 复用抽取能力，数据库版本策略由本项目控制 |
| [Mem0](https://github.com/mem0ai/mem0) | 库、自托管及托管入口；Apache-2.0 | 选择开源库作对照，不默认注册托管账号 |
| [Hindsight](https://github.com/vectorize-io/hindsight) | 显式 retain/recall/reflect 操作、独立记忆空间；MIT | 第二个现成系统对照 |
| [Graphiti](https://github.com/getzep/graphiti) | 动态关系、来源与历史时间查询；Apache-2.0 | 借鉴时间设计，第一版不加图数据库 |
| [Deep Agents](https://github.com/langchain-ai/deepagents) | 上下文压缩、文件工具、持久记忆等；MIT | 调研新方向，后期作运行方式对照 |
| [Langfuse](https://github.com/langfuse/langfuse) | 调用记录、数据集和实验界面；核心 MIT，ee 目录除外 | 可选，不让部署界面拖慢第一周 |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | Python 自定义调用、回归测试和比较；MIT | 中文案例回归可用，官方评分仍单独保留 |
| [Phoenix](https://github.com/Arize-ai/phoenix) | 可自托管的执行记录与评测；ELv2 | 源码可用但不是 MIT/Apache 类宽松开源授权，主线不选 |
| [旧 memory-template](https://github.com/langchain-ai/memory-template) | GitHub 标记 2026-08-21 已归档 | 仅参考思路，不作为新项目底座 |

许可依据均来自对应仓库的 LICENSE 或官方说明；第三方依赖仍有各自授权。保留原作者版权和变更说明即可从主线继续开发，不需要额外的预先审批环节。

## 3. 最近值得关注的变化

### 3.1 执行框架开始自带上下文管理

Deep Agents 把压缩、文件式保存、长期记忆等能力放进框架。它有助于快速做长任务，但也会增加实验中的隐含变量。

本项目先使用小模板，控制自己的记忆与输入选择；以后接 Deep Agents 时，逐项记录其自动摘要、额外模型调用及输入长度，避免把框架自带功能误算为自研效果。[源码](https://github.com/langchain-ai/deepagents)、[上下文文档](https://docs.langchain.com/oss/python/deepagents/context-engineering)

### 3.2 记忆系统从保存片段，发展到保存并综合信息

Hindsight 提供 retain（保存）、recall（找回）、reflect（综合生成）等入口。这些能力可以作强参照，但其网站上的成绩是上游报告，不是本项目复现。

比较“记忆检索”时优先使用 recall，最终回答仍交给统一的回答模型。若使用 reflect，把其内部生成和费用作为整套系统实验另外报告。[源码与快速开始](https://github.com/vectorize-io/hindsight)

### 3.3 评测开始重视后续行动与经验

MemoryArena 观察历史信息怎样影响下一次任务；LongMemEval-V2 使用 web 和 enterprise 两类环境的历史操作轨迹，包含 451 个问题，覆盖状态、流程经验和环境特例等能力。

V2 的输入形态和普通聊天不同，还有多模态与大规模历史的处理成本，因此放在本项目完成后的扩展列表，不能仅因它更新就取代第一版主评测。[MemoryArena](https://memoryarena.github.io/)、[LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2)

### 3.4 新模型能力要和任务需要匹配

已核对 Qwen3 文本检索模型及 Qwen3-VL 多模态检索模型的官方页面。当前项目以文字历史为主，先用较小文本模型，固定其版本与输入格式；多模态检索留给包含截图的扩展。

本文不宣称这些是整个行业最新、排名第一或对所有语言最优的选择。选择依据是公开可用、文档清楚、成本适合个人项目。[文本模型](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)、[多模态模型](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)

## 4. 源码核对发现

### 4.1 模板 README 与当前代码不能混为一谈

所核对的 `react-agent` README 有早期模型和 Studio 相关描述；当前代码已经使用 `Runtime[Context]`，模型加载函数按 `provider/model` 分割名称。

修改前先读 `graph.py`、`context.py` 和 `utils.py`，不把旧教程的配置方式直接贴进当前代码。[固定源码](https://github.com/langchain-ai/react-agent/tree/5c15518f0f08fbd97b1c8b6437db6656e3920229/src/react_agent)

### 4.2 LangMem 的抽取入口和自动写 Store 的入口不同

已核对 `create_memory_manager`、`create_memory_store_manager` 和独立 Store 示例。主线选择先产生结构化候选，再进入自己的校验与版本记录；不把模型自动覆盖视为已经完成严格的历史版本管理。

示例中的内存 Store 只适合起点验证，重启后数据会丢失。[接口](https://langchain-ai.github.io/langmem/reference/memory/)、[独立存储示例](https://github.com/langchain-ai/langmem/blob/48e3c11f5bb527282c7d5339c6a87a0b35abccfc/examples/standalone_examples/custom_store_example.py)

### 4.3 LongMemEval 评分程序有固定别名与旧依赖

在所核对的 `evaluate_qa.py` 中，命令行第一个评分参数会先查 `model_zoo`，不支持的名称会退出。README 中旧日志文件描述也不应作为代码入口契约。

它的 `requirements-lite.txt` 包含 `openai==1.35.1` 等旧依赖，因此评分器单独建立环境；如迁移客户端，保留评分规则、模型映射和改动记录。[评分源码](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/evaluation/evaluate_qa.py)、[依赖文件](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/requirements-lite.txt)

### 4.4 MemoryArena 的 none 不能直接叫作无历史

固定快照的 `run_travel.py` 在没有 memory_system 时，把 `include_previous_plans` 设为真；Agent 会加入前面计划和已有问题。

因此报告时把这一设置写成“上游 none 默认设置”。本项目真正的无跨会话记忆需要包装层另外控制，并检查上下文内容。[运行器](https://github.com/ZexueHe/MemoryArena/blob/6cd9de14b71915e39ac742a20dc33785e14b6aab/run_travel.py)、[Agent](https://github.com/ZexueHe/MemoryArena/blob/6cd9de14b71915e39ac742a20dc33785e14b6aab/agent/travel_planner.py)

### 4.5 MemoryArena 的缺失输出与评分口径需要额外核查

固定快照的评分按提交组和参考组的交集、以及已提交参与者遍历。若只生成部分结果，直接读取输出分数可能遗漏失败项。

本项目按固定任务清单做完整性检查，缺失项填失败记录；同时保存上游原始指标与补齐后的指标，公开说明差异。其槽位比较包含字符串相似度，不能声称它等价于完整业务正确性。[评分源码](https://github.com/ZexueHe/MemoryArena/blob/6cd9de14b71915e39ac742a20dc33785e14b6aab/env/env_systems/travel_planner_env/eval.py)

### 4.6 MemoryArena 的输入、反馈与等待方式

运行器读取任务时也会接触答案，Agent 的可见输入必须单独筛选；基础人的既定计划是合法背景，后续人的标准答案不能混入。主实验关闭 hint/answer 反馈。

部分示例为某些记忆后端写入后固定等待。正式实现根据写入/索引状态判断，不能把固定等待秒数当成所有后端的通用要求。[设置说明](https://github.com/ZexueHe/MemoryArena/blob/6cd9de14b71915e39ac742a20dc33785e14b6aab/setup_travel.md)、[运行器](https://github.com/ZexueHe/MemoryArena/blob/6cd9de14b71915e39ac742a20dc33785e14b6aab/run_travel.py)

### 4.7 数据授权与代码授权分开核对

MemoryArena 官方项目页将数据标为 CC-BY-4.0；所检查代码树没有单独 LICENSE。本项目使用其公开数据和独立复现入口，不把其代码复制进要重新发布的主应用。业务工具优先参考明确 MIT 授权的 TravelPlanner。

LoCoMo 适合做补充记忆实验，但数据有非商业限制。主线已有足够数据，第一版不再扩充一个同类评测。[MemoryArena 数据许可](https://memoryarena.github.io/)、[TravelPlanner](https://github.com/OSU-NLP-Group/TravelPlanner/blob/main/LICENSE)、[LoCoMo 论文附录](https://aclweb.org/anthology/2024.acl-long.747.pdf)

## 5. 需要自己开发的内容

| 内容 | 复用已有部分 | 自己负责的差异 |
|---|---|---|
| Agent 流程 | 官方模板 | 增加记忆读取、预算内组装和结果检查节点 |
| 信息抽取 | LangMem | 限定字段、来源校验、明确事实与建议 |
| 持久保存 | PostgreSQL 与 LangGraph 存储 | 事实版本、范围、来源和索引更新规则 |
| 搜索 | 现成文本模型、数据库搜索 | 查询策略、过滤、去重和选取 |
| 任务工具 | TravelPlanner 的许可明确代码 | 适配本项目统一输入输出 |
| 评测 | 公开数据、上游规则 | 清单隔离、标签剥离、完整分母、成本记录 |
| 演示 | Streamlit | 记忆变化、引用、计划和运行记录面板 |

代码复用情况写进 README：哪些直接使用，哪些修改，哪些仅参考思想。面试时能够准确区分自己的贡献。

## 6. 固定的代码快照

下表日期为所核对最新提交的北京时间日期，不表示当日发布了对应软件包。完整 SHA 与提交 URL 在 JSON 附件里。

| 项目 | 提交日期 | 固定提交 |
|---|---|---|
| langchain-ai/langgraph | 2026-10-24 | [4c52e129eb](https://github.com/langchain-ai/langgraph/commit/4c52e129eb1ab69a3da58b799f67929f77d81149) |
| promptfoo/promptfoo | 2026-10-23 | [c0b88a3241](https://github.com/promptfoo/promptfoo/commit/c0b88a324175c60019cc80de1b2e32b4c849d4c3) |
| vectorize-io/hindsight | 2026-10-24 | [b4a0da1e9f](https://github.com/vectorize-io/hindsight/commit/b4a0da1e9fd2dfd052843e4f95fcf368301f6a73) |
| mem0ai/mem0 | 2026-10-21 | [2c81af3bbe](https://github.com/mem0ai/mem0/commit/2c81af3bbe27d9bccb09c772d583df9e9be72ee5) |
| getzep/graphiti | 2026-10-24 | [3ffc978753](https://github.com/getzep/graphiti/commit/3ffc978753a95fb5f363d4f6509b65ac023379cc) |
| langfuse/langfuse | 2026-10-24 | [f3500cd116](https://github.com/langfuse/langfuse/commit/f3500cd1167ec459851730913ebbb94c5003535c) |
| langchain-ai/deepagents | 2026-10-24 | [a3381668c4](https://github.com/langchain-ai/deepagents/commit/a3381668c4d3b558742101fa7e6b8fe4a64e56ef) |
| langchain-ai/react-agent | 2026-10-23 | [5c15518f0f](https://github.com/langchain-ai/react-agent/commit/5c15518f0f08fbd97b1c8b6437db6656e3920229) |
| xiaowu0162/LongMemEval | 2026-05-12 | [9e0b455f4e](https://github.com/xiaowu0162/LongMemEval/commit/9e0b455f4ef0e2ab8f2e582289761153549043fc) |
| xiaowu0162/LongMemEval-V2 | 2026-08-10 | [2cc8c540bd](https://github.com/xiaowu0162/LongMemEval-V2/commit/2cc8c540bdb87fe6761629b585e727e1c4704520) |
| OSU-NLP-Group/TravelPlanner | 2026-05-24 | [e52c87f4ac](https://github.com/OSU-NLP-Group/TravelPlanner/commit/e52c87f4ac348a3410c46dc3553c519db5ec5e23) |
| ZexueHe/MemoryArena | 2026-06-01 | [6cd9de14b7](https://github.com/ZexueHe/MemoryArena/commit/6cd9de14b71915e39ac742a20dc33785e14b6aab) |
| langchain-ai/langmem | 2026-10-03 | [48e3c11f5b](https://github.com/langchain-ai/langmem/commit/48e3c11f5bb527282c7d5339c6a87a0b35abccfc) |

## 7. 版本核对与首次联调

软件包版本从各自 PyPI JSON 接口读取，详见 research-snapshot.json。候选版本与主分支快照可能不同，首次联调通过后以 uv.lock 为安装依据。

已完成：核对公开来源、主要代码入口、数据结构、授权说明及版本信息。

待开发阶段完成：依赖组合安装、模型接口可用性、数据库和向量维度配置、全部数据下载、端到端运行及基线成绩。本文没有用上游宣传分数充当自己的结果。

建议联调顺序：模型与单工具 → LangMem 单次抽取 → 数据库存取及重启 → 10 题完整评测 → 接任务环境 → 加外部记忆对照。每次只引入一个变量，便于定位失败。
