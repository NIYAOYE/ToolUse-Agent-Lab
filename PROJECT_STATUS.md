# Project Status

## 1. Project Goal

将现有不依赖 RAG 的 Tool-Use Agent 演进为 SupportOps 工单调查工作台：面向研发与运维
技术支持工程师，使用 Qwen、Tavily、受限文件读取和受限 Python 分析工单，生成带证据的
结构化诊断方案，由人工审批，并以首次诊断时间衡量效率。

## 2. Current Architecture

主要调用链为：CLI/HTTP 请求 -> FastAPI -> `ChatService` -> LangGraph Agent -> Qwen
Function Calling -> 工具注册中心 -> Tavily / 文件读取 / Python 执行。会话消息、历史摘要和
工具审计记录由 SQLite 仓库持久化，`composition.py` 负责从环境变量读取配置并装配运行时依赖。

已确认的目标架构将在现有 Agent 内核外新增 React 工单工作台、工单领域模型、
`TicketService`、`InvestigationService`、结构化诊断报告、证据链、人工审批和诊断耗时指标。
完整设计与阶段边界见 `SUPPORTOPS_EVOLUTION_PLAN.md`。

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
- [x] 将完整功能本地合并到 `main`，并通过 Pull Request #2 合入远端 `main`
- [x] 保留本地与远端 `develop` 分支及其 worktree
- [x] 完成 SupportOps 产品定位、前端信息架构、工业控制台视觉方向和技术架构设计
- [x] 编写 SupportOps 多 Agent 演进主文档与八阶段交付路线

## 4. In Progress

- [ ] Phase 1：工单领域底座，包括模型、SQLite 仓库和状态机

## 5. TODO / Next Steps

- [ ] Phase 1：工单、附件、调查、证据、诊断和审批领域底座
- [ ] Phase 2：工单创建、导入、列表、详情和附件 API
- [ ] Phase 3：结构化工单调查引擎
- [ ] Phase 4：调查 SSE、审批和首次诊断时间 API
- [ ] Phase 5：React/Vite 前端底座和工业控制台设计系统
- [ ] Phase 6：三栏核心调查工作台
- [ ] Phase 7：导入、指标看板和审计详情
- [ ] Phase 8：演示数据、真实 API 验证和安全硬化

## 6. Known Issues

- `python_exec` 适合本地演示和半可信输入，不是可安全执行恶意代码的生产级沙箱。
- HTTP API 当前没有认证和限流，不应直接暴露到公网。
- 真实 API 冒烟测试会消耗 Qwen 与 Tavily 配额，默认测试流程不会自动执行这些用例。
- 远端 `main` 启用了“必须通过 Pull Request 修改”的保护规则，不能直接 `git push main`。
- 本轮创建最终文档 PR 时，Codex 外部授权服务达到用量上限；状态分支已推送，但 PR 尚未创建。
- SupportOps 仍处于设计完成、实现未开始阶段；当前代码只有通用聊天和工具调用能力。
- MVP 不包含 RAG、自动执行生产修复、自动关闭工单或真正的多 Agent 运行时。

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
| `SUPPORTOPS_EVOLUTION_PLAN.md` | SupportOps 产品设计、前端方向、架构、API、路线与协作规则 |

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

SupportOps 演进文档完成后执行：

```powershell
Select-String -Path SUPPORTOPS_EVOLUTION_PLAN.md `
  -Pattern 'TBD','TODO','implement later','fill in','待定','稍后实现' -SimpleMatch
git diff --check
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
```

结果：文档无占位符，八个阶段齐全，Markdown 代码围栏成对；`git diff --check` 通过；
回归测试 `49 passed, 1 skipped, 3 deselected`；编译检查通过。

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

### Agent Update - 2026-06-14 23:45

本轮 Agent 完成内容：

* 直接推送 `main` 被仓库规则 `GH013` 拒绝，确认该分支要求所有变更通过 Pull Request。
* 通过 GitHub 合并 PR #2，远端合并提交为 `f45716b`；没有删除 `develop` 分支。
* 远端 `main` 现已包含完整 Agent 代码、测试、README 和首版 `PROJECT_STATUS.md`。
* 已推送 `codex/finalize-project-status` 分支，用于同步本轮新增的最终状态记录。
* 创建该文档 PR 时，Codex 外部授权服务达到用量上限，网络操作被平台拒绝；不是 GitHub
  仓库、认证或代码错误。
* 下一位 Agent 应先从 `codex/finalize-project-status` 向 `main` 创建并合并 PR，然后执行
  `git fetch origin`，将本地 `main` 快进到 `origin/main`；继续保留 `develop` 分支。

### Agent Update - 2026-06-15 05:24

本轮 Agent 完成内容：

* 结合现有 Tool-Use Agent 能力与用户提供的产品建议，将演进方向确定为 SupportOps 工单调查工作台。
* 明确目标用户为研发与运维技术支持工程师，MVP 采用手动创建和 CSV/JSON 导入工单。
* 明确 Agent 只生成带证据的诊断建议，由人工批准、编辑后批准或退回重查。
* 确定前端为 React 三栏工作台，并选择工程图纸、硬边框、警示橙和人工签署章的工业控制台视觉方向。
* 确定工单领域模型、调查状态机、API、结构化诊断契约、安全边界、测试策略和八阶段开发路线。
* 新增 `SUPPORTOPS_EVOLUTION_PLAN.md`，作为后续多对话、多 Agent 开发的主设计与协作基线。
* 完成文档占位符、一致性、Markdown 结构检查，并运行非 live 回归测试和编译检查，结果通过。
* 本轮只修改文档，没有开始 Phase 1 业务代码；下一位 Agent 应先实现工单领域底座。
