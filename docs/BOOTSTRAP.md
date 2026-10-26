# 基础搭建记录

日期：2026-10-26（北京时间）。

## 已完成

- 项目现位于用户指定的文稿/Projects/Code/memorypilot，已从原 Project/code 目录迁移。
- 从 MIT 授权的 LangGraph 官方模板开始，保留来源与许可证。
- 本项目内安装 uv 0.13.5、Python 3.12.15、.venv 和锁定依赖。
- 配置 DeepSeek 官方 Chat Completions 接口，模型标识 deepseek-v4-pro。
- 接入 LangMem、SQLite 事实版本、LangGraph 检查点、命令行与本地 HTTP API。
- 增加上下文、工具次数、模型次数、时间上限。
- 测试使用模拟 HTTP 验证真实客户端的请求地址、模型参数及思考模式协议字段。
- 增加 LongMemEval 数据转换入口，并剥离评分标签。

## 与原计划的环境差异

当前机器没有 Docker，先让 SQLite 承担开发存储；PostgreSQL 作为明确未接入的可选配置保留。Python 采用实际成功安装的 3.12.15，不要求改动系统 Python 3.9。

PyPI 的文件服务器出现 TLS 连接失败，改用清华 PyPI 镜像完成依赖安装。所有实际依赖固定在 uv.lock，环境恢复使用 scripts/setup.sh。

## 模型联调状态

当前没有配置 DEEPSEEK_API_KEY，因此没有向真实 DeepSeek 服务发送生成请求。API 接入代码与报文通过模拟 HTTP 测试；模型回答质量、密钥权限、实际额度仍需填入密钥后验证。

默认关闭思考模式，记忆抽取也固定使用非思考请求，以兼容结构化抽取的工具选择。思考模式工具调用的回传字段单独修复并测试。

## 数据和评测状态

本地目录使用少量虚构酒店。离线 smoke 仅验证记忆更新和工具循环，不是公开基准成绩。完整评测与向量检索仍按开发计划推进。

## 实际验证

- 27 项自动测试通过。
- Ruff 检查与格式检查通过。
- scripts/setup.sh 重复运行通过。
- 离线流程检查 3/3 通过，所有结果标记为 mock。
- 实际启动本地 HTTP 服务，健康检查、对话、记忆读取通过；验证后已停止测试进程。
- git diff --check 通过。

有两条来自上游库的弃用提示，当前不影响上述测试。依赖固定在 uv.lock，后续升级需重新验证。

## 目录迁移验证

2026-10-26：项目已迁移至 `/Users/lican/Documents/Projects/Code/memorypilot`，配置、数据和 Git 修改均保留。已在新目录重建虚拟环境，并通过 27 项测试、Ruff 检查及离线演示；原项目目录已移除。
