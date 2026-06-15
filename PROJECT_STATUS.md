# Project Status

## 1. Project Goal

构建一个不依赖 RAG 的 Tool-Use Agent 实验项目：使用 LangGraph 编排推理与工具调用，
通过阿里云百炼 Qwen API 完成模型推理，集成 Tavily 搜索、受限文件读取和受限 Python
执行，并提供 SQLite 多轮会话持久化、FastAPI/SSE 服务与终端客户端。

## 2. Current Architecture

主要调用链为：CLI/HTTP 请求 -> FastAPI -> `ChatService` -> LangGraph Agent -> Qwen
Function Calling -> 工具注册中心 -> Tavily / 文件读取 / Python 执行。会话消息、历史摘要和
工具审计记录由 SQLite 仓库持久化，`composition.py` 负责从环境变量读取配置并装配运行时依赖。

## 3. Completed Work

- [x] 项目配置、环境变量读取与 Qwen 客户端
- [x] Tavily 网页搜索工具与统一工具注册中心
- [x] 工作目录内的受限文件读取工具
- [x] 基于 AST、隔离进程、超时和输出限制的 Python 执行工具
- [x] LangGraph 推理与工具调用循环
- [x] SQLite 会话、消息、摘要和工具审计持久化
- [x] 多轮对话服务与历史压缩
- [x] FastAPI REST/SSE 接口及依赖装配
- [x] HTTP/SSE 终端客户端与项目运行文档
- [x] 本地单元测试和真实 Qwen/Tavily API 冒烟测试
- [x] 将完整功能本地合并到 `main` 并创建 Pull Request #2

## 4. In Progress

- [ ] 将本地 `main` 的合并结果同步到远端，并让保留的 `develop` 与最终状态对齐

## 5. TODO / Next Steps

- [ ] 为 HTTP API 增加认证、限流和生产环境配置
- [ ] 将 Python 执行从本地受限子进程升级为容器或虚拟机级隔离
- [ ] 增加结构化日志、指标、链路追踪和部署配置
- [ ] 根据后续演示需求补充端到端场景测试

## 6. Known Issues

- `python_exec` 适合本地演示和半可信输入，不是可安全执行恶意代码的生产级沙箱。
- HTTP API 当前没有认证和限流，不应直接暴露到公网。
- 真实 API 冒烟测试会消耗 Qwen 与 Tavily 配额，默认测试流程不会自动执行这些用例。

## 7. Important Files

| File / Directory | Purpose |
| --- | --- |
| `src/tool_use_agent/agent/` | LangGraph 状态、提示词和工具调用循环 |
| `src/tool_use_agent/tools/` | Tavily、文件读取、Python 执行和工具注册 |
| `src/tool_use_agent/memory/` | SQLite 数据模型与持久化仓库 |
| `src/tool_use_agent/llm/` | Qwen 客户端和历史摘要器 |
| `src/tool_use_agent/service.py` | 多轮会话、历史压缩和工具审计编排 |
| `src/tool_use_agent/api/` | FastAPI 路由、请求模型与 SSE 编码 |
| `src/tool_use_agent/composition.py` | 配置读取和运行时依赖装配 |
| `src/tool_use_agent/cli.py` | HTTP/SSE 终端客户端 |
| `tests/` | 单元、集成和真实 API 冒烟测试 |
| `README.md` | 安装、运行、API、测试和安全边界说明 |

## 8. Validation

```powershell
& 'D:\miniconda3\envs\agent\python.exe' -c "import os; ..."
```

结果：`DASHSCOPE_API_KEY` 与 `TAVILY_API_KEY` 均可从环境变量读取，未输出密钥内容。

```powershell
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q
```

结果：通过，`49 passed, 1 skipped, 3 deselected`。

```powershell
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
```

结果：通过，无编译错误。

```powershell
& 'D:\miniconda3\envs\agent\python.exe' -m pytest tests/live/test_live_smoke.py `
  -m live -q -s --basetemp .pytest_tmp\live-20260614-2338 -p no:cacheprovider
```

结果：通过，`3 passed`。首次执行时用户级 pytest 临时目录发生 `WinError 5`，改用项目内
已忽略的 `.pytest_tmp` 后验证通过；这是执行环境权限问题，不是业务测试失败。

本地合并到 `main` 后再次执行：

```powershell
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
git diff --exit-code develop main
```

结果：测试通过，`49 passed, 1 skipped, 3 deselected`；编译检查通过；合并后的文件树与
`develop` 一致。

## 9. Change Log

### Agent Update - 2026-06-14 23:39

本轮 Agent 开始内容：

* 核对了 `main`、`develop`、远端跟踪分支和 Git worktree 状态。
* 检查了项目目录、配置、README、测试文件和最近提交。
* 创建本协作状态文档，当前任务是验证并将 `develop` 集成到 `main`。
* 完成非实时测试、编译检查和真实 Qwen/Tavily API 冒烟测试，全部通过。
* 下一步提交状态文档，再进行本地合并、Pull Request 和远端同步。

### Agent Update - 2026-06-14 23:42

本轮 Agent 完成内容：

* 将 `develop` 无冲突合并到本地 `main`，合并提交为 `53c4bde`。
* 发现远端 `main` 已通过 PR #1 合并早期三个模块，并在该真实基线上完成后续集成。
* 在合并后的 `main` 上重新运行测试、编译检查和分支文件树比较，结果均通过。
* 创建 `develop -> main` 的 Pull Request #2：
  `https://github.com/NIYAOYE/ToolUse-Agent-Lab/pull/2`。
* 下一步推送 `main`，确认 PR 远端状态后同步并保留 `develop` 分支。
