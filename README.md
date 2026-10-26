# MemoryPilot

一个基于 LangGraph 官方 ReAct 模板和 LangMem 的多会话任务助理。

当前是**可运行的基础版本**：支持 DeepSeek 官方 API、可持久保存的记忆、预算修改历史、上下文长度检查、工具调用、本地 HTTP API 和离线测试。

## 1. 先运行

进入本项目目录：

```bash
cd /Users/lican/Documents/Projects/Code/memorypilot
./run.sh doctor
./run.sh demo
```

`doctor` 检查配置，不发模型请求。`demo` 使用临时数据库和明确标记的模拟模型，不消耗 API 额度，也不污染正式记忆。

本次已经在项目中安装 Python 3.12 与依赖。以后重新搭建，执行：

```bash
bash scripts/setup.sh
```

运行工具和 Python 安装在 `.tools/`，虚拟环境在 `.venv/`；无需修改系统 Python 或 shell 配置。依赖由 `uv.lock` 固定。此次 PyPI 文件下载遇到 TLS 连接失败，已使用清华 PyPI 镜像安装，锁文件保留了实际下载源。

## 2. 调用 DeepSeek V4 Pro

编辑本地 `.env`：

```dotenv
MEMORYPILOT_PROVIDER=deepseek
DEEPSEEK_API_KEY=填写你自己的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_THINKING=false
```

密钥只填在本地文件，不需要发送到聊天。`.env` 已被 Git 忽略，文件权限为仅当前用户可读写。

然后发送消息：

```bash
./run.sh chat '我的住宿预算每晚500元，不吃海鲜。' --session session-1
./run.sh chat '我的住宿预算改为每晚700元。' --session session-2
./run.sh chat '请推荐酒店。' --session session-3
./run.sh memories --history
```

这三次请求属于同一默认用户和旅行，使用不同会话。需要隔离时传入 `--user`、`--trip`、`--namespace`：

```bash
./run.sh chat '住宿预算每晚600元。' --user alice --trip trip-001 --namespace dev --session s1
./run.sh memories --user alice --trip trip-001 --namespace dev --history
```

没有密钥时，DeepSeek 模式会明确报错，**不会自动切换模拟答案**。想用持久数据库测试本地流程，请明确指定：

```bash
./run.sh chat '住宿预算每晚500元。' --provider mock
```

真实请求会用 DeepSeek 抽取当前要求，再调用生成模型回答。一次对话可能包含一次抽取和多次生成调用，请先用一条短消息验证接口。当前生成模型的用量会记录；LangMem 抽取内部用量尚未汇总，因此现在不能声称已统计完整费用。

官方来源：[模型标识与接口](https://api-docs.deepseek.com/quick_start/agent_integrations/)、[工具调用](https://api-docs.deepseek.com/guides/tool_calls/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)。

## 3. 现在已经有什么

| 模块 | 已实现 |
|---|---|
| Agent 基础 | 复用模板的 LangGraph 模型—工具循环 |
| 模型接口 | DeepSeek V4 Pro；可配置地址、模型、超时与思考开关 |
| 真实信息抽取 | 使用 LangMem，接收结构化候选事实 |
| 离线模式 | 窄范围、规则驱动的模拟模型与抽取器；仅做流程检查 |
| 持久记忆 | SQLite 保存原文、追加事实版本及来源 |
| 更新与查询 | 当前预算、旧版本、按已知时间查询；重复事实不重复建版本 |
| 数据隔离 | 用户、旅行、实验范围；工具读取来源时也检查范围 |
| 上下文 | 必须约束优先、原文来源、超长证据舍弃、预算超限中止 |
| 工具 | 查询虚构酒店、读取当前范围内原文 |
| 运行限制 | 生成调用次数、工具次数、任务时间和输出长度上限 |
| 日志 | 结构化运行记录，不导出密钥或模型内部推理字段 |
| 本地接口 | 健康检查、发送消息、查看记忆 |
| 评测基础 | 离线流程检查、LongMemEval 输入与评分标签分离适配器 |

当前上下文长度使用 UTF-8 字节作为保守估算，**不是 DeepSeek 的准确 token 数**。模型实际返回的用量另行记录。长会话超过预算会中止，不会悄悄丢掉尚未处理的工具调用。

DeepSeek 思考模式的工具协议需要回传 `reasoning_content`。当前适配器补上了已安装库遗漏的序列化行为，并有 HTTP 模拟测试；默认仍关闭思考模式。开启后，该字段仅为协议延续保存在检查点消息中，不作为事实提取、API 回答或导出日志。

## 4. 本地 HTTP 接口

```bash
./run.sh serve
```

地址为 `http://127.0.0.1:8000`，交互接口说明在 `http://127.0.0.1:8000/docs`。

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"我的住宿预算每晚500元。","session_id":"s1","scope":{"user_id":"demo","trip_id":"hangzhou","namespace":"dev"}}'
curl 'http://127.0.0.1:8000/memories?user=demo&trip=hangzhou&namespace=dev&history=true'
```

`/chat` 使用 `.env` 选择的模式。缺少真实密钥时返回 503；`/health` 不调用生成模型。API 当前用于本地开发，没有账号认证，不作为公网服务发布。

离线体验 HTTP 接口：

```bash
MEMORYPILOT_PROVIDER=mock ./run.sh serve
```

## 5. 测试与评测流程检查

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
./run.sh eval-smoke
```

`eval-smoke` 输出到 `results/smoke/`，每次使用独立实验空间，失败用例也计入分母。输出明确标注 `provider=mock` 和 `scientific_benchmark=false`。

**它不是 LongMemEval、MemoryArena 或 DeepSeek 的质量成绩。** 这两套公开评测的完整运行器、模型评分和费用对照，下一阶段再接入。

自动测试使用临时数据库和模拟 HTTP，不依赖真实 API 密钥，不消耗模型额度。

## 6. 代码在哪里

```text
src/
  react_agent/              # 从官方模板改造的 Agent 循环
    graph.py                # 模型—工具循环及运行限制
    state.py                # 消息、调用计数和截止时间
  memorypilot/
    config.py               # .env 配置
    schemas.py              # 数据格式
    providers.py            # DeepSeek 客户端、V4 协议修正和模拟模型
    extraction.py           # LangMem 抽取与离线抽取
    repository.py           # SQLite、来源与版本
    context_builder.py      # 必要约束和证据选择
    tools.py                # 范围绑定工具和虚构酒店资料
    service.py              # 应用入口
    api.py                  # 本地 HTTP 接口
    cli.py                  # 命令行
    evaluation.py           # 流程检查与数据转换
tests/
docs/
scripts/setup.sh
run.sh
compose.yaml                # 可选 PostgreSQL 服务配置
uv.lock
```

正式本地数据在 `.data/`：

- `memory.sqlite3`：原文、事实版本和运行摘要。
- `checkpoints.sqlite3`：同一会话的执行状态。
- `traces/`：脱离客户端对象的运行记录。

换新会话使用不同 `--session`；换实验使用不同 `--namespace`。这两个概念不同：会话可以共享同一用户、旅行下的长期记忆，实验应互不干扰。

## 7. 与完整开发文档相比，还没做什么

当前先把环境和第一条运行链路搭好。以下内容尚未实现：

- PostgreSQL 业务存储适配；现有 compose 文件只启动数据库，不会自动切换应用。
- 向量检索、Qwen 检索模型和重排序；当前只有最近原文及简单词项相关度排序。
- 多人关系、未来生效时间、明确撤销和全面删除；当前事实仅代表当前用户本次旅行的字面要求。
- 完整行程生成、约束求解、真实交通和餐厅工具；现有酒店目录是虚构测试资料。
- Mem0/Hindsight 对照、完整公开数据评测、自动评分和完整成本汇总。
- 生产环境认证、并发任务恢复、前端界面。

文字事实当前只接收原文中直接出现的值，并检查引用；无法直接核对的抽取会拒绝写入。用户换说法、隐含表达和复杂时间需要后续完善，不能将这版描述为已解决所有长期记忆问题。

## 8. 开源来源和开发记录

基础仓库：[langchain-ai/react-agent](https://github.com/langchain-ai/react-agent)，固定起点：

`87aac0fdcb811d05457314a42418f3fbe139933a`（2026-10-25 提交）。

保留上游 MIT LICENSE；主要复用 LangGraph 的状态、模型—工具循环和 ToolNode，并在上面加入记忆与应用入口。LangMem 负责真实接口模式的信息抽取，不重新实现一套抽取框架。

更多资料：

- [开发设计原稿](docs/MemoryPilot-开发文档.md)
- [开源调研原稿](docs/MemoryPilot-开源调研与选型.md)
- [本次实际搭建记录](docs/BOOTSTRAP.md)
- [第三方来源](THIRD_PARTY_NOTICES.md)

设计原稿中的版本和步骤是 2026-10-24 的规划，实际环境以本仓库 `uv.lock` 和搭建记录为准。
