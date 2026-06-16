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
- [x] 完成 Phase 1 首个切片：工单模型、状态机和 SQLite 工单仓库
- [x] 完成 Phase 1：附件、调查、证据、诊断和审批模型及 SQLite 关系
- [x] 完成 Phase 2 首个切片：手动创建、分页筛选列表与详情 API
- [x] 完成 Phase 2：CSV/JSON 原子导入与受控附件上传 API
- [x] 完成 Phase 3：结构化工单调查 Runner、证据链、诊断报告校验和失败状态
- [x] 完成 Phase 4：调查启动/重试、SSE 恢复、人工审批和首次诊断时间 API
- [x] 完成 Phase 5：React/Vite 前端底座、应用 Shell、路由、typed API client 和设计 token

## 4. In Progress

- Phase 6：实现三栏核心调查工作台与真实 SupportOps API 交互。

## 5. TODO / Next Steps

- [ ] Phase 6：三栏核心调查工作台
- [ ] Phase 7：导入、指标看板和审计详情
- [ ] Phase 8：演示数据、真实 API 验证和安全硬化

## 6. Known Issues

- `python_exec` 适合本地演示和半可信输入，不是可安全执行恶意代码的生产级沙箱。
- HTTP API 当前没有认证和限流，不应直接暴露到公网。
- 真实 API 冒烟测试会消耗 Qwen 与 Tavily 配额，默认测试流程不会自动执行这些用例。
- 远端 `main` 启用了“必须通过 Pull Request 修改”的保护规则，不能直接 `git push main`。
- 本轮创建最终文档 PR 时，Codex 外部授权服务达到用量上限；状态分支已推送，但 PR 尚未创建。
- SupportOps 已完成 Phase 1-5；三栏工作台、审计视图和演示硬化尚未实现。
- MVP 不包含 RAG、自动执行生产修复、自动关闭工单或真正的多 Agent 运行时。
- `agent` 环境的可编辑安装可能指向其他 worktree；验证当前工作区代码时可显式设置
  `PYTHONPATH` 为仓库内的 `src/`，或重新安装当前工作区。

## 7. Important Files

| File / Directory | Purpose |
| --- | --- |
| `src/tool_use_agent/agent/` | LangGraph 状态、提示词和工具调用循环 |
| `src/tool_use_agent/tools/` | Tavily、文件读取、Python 执行和工具注册 |
| `src/tool_use_agent/memory/` | SQLite 数据模型与持久化仓库 |
| `src/tool_use_agent/llm/` | Qwen 客户端和历史摘要器 |
| `src/tool_use_agent/service.py` | 多轮会话、历史压缩和工具审计编排 |
| `src/tool_use_agent/api/` | FastAPI 路由、请求模型与 SSE 编码 |
| `src/tool_use_agent/api/tickets.py` | 工单创建、列表、详情路由与稳定错误体 |
| `src/tool_use_agent/composition.py` | 配置读取和运行时依赖装配 |
| `src/tool_use_agent/cli.py` | HTTP/SSE 终端客户端 |
| `src/tool_use_agent/tickets/` | 工单领域模型、状态机和独立 SQLite 仓库 |
| `src/tool_use_agent/tickets/service.py` | 工单创建、查询、原子导入和受控附件存储编排 |
| `src/tool_use_agent/investigations/` | 调查、证据、诊断报告和审批领域模型 |
| `src/tool_use_agent/investigations/runner.py` | 结构化工单上下文、Agent 调用、证据/报告持久化和失败状态编排 |
| `src/tool_use_agent/investigations/prompts.py` | 结构化诊断 JSON 契约与调查安全边界提示词 |
| `src/tool_use_agent/investigations/service.py` | 调查启动、同上下文重试、运行、审批、事件和指标编排 |
| `src/tool_use_agent/api/investigations.py` | 调查启动、详情、SSE、审批和诊断耗时路由 |
| `src/tool_use_agent/api/investigation_models.py` | Phase 4 调查、证据、事件、审批和指标 API 模型 |
| `frontend/` | React/Vite 应用、路由、查询客户端、工业控制台组件与样式 token |
| `frontend/src/lib/api.ts` | typed JSON 请求、稳定错误体解析与 `ApiError` |
| `frontend/src/components/AppShell.tsx` | SupportOps 顶栏、编号导航、主内容区与底部状态栏 |
| `tests/` | 单元、集成和真实 API 冒烟测试 |
| `README.md` | 安装、运行、API、测试和安全边界说明 |
| `SUPPORTOPS_EVOLUTION_PLAN.md` | SupportOps 产品设计、前端方向、架构、API、路线与协作规则 |

## 8. Validation

```powershell
python -c "import os; ..."
```

结果：`DASHSCOPE_API_KEY` 与 `TAVILY_API_KEY` 均可从环境变量读取，未输出密钥内容。

```powershell
python -m pytest -m "not live" -q
```

结果：通过，`49 passed, 1 skipped, 3 deselected`。

```powershell
python -m compileall -q src tests
```

结果：通过，无编译错误。

```powershell
python -m pytest tests/live/test_live_smoke.py `
  -m live -q -s --basetemp .pytest_tmp\live-20260614-2338 -p no:cacheprovider
```

结果：通过，`3 passed`。首次执行时用户级 pytest 临时目录发生 `WinError 5`，改用项目内
已忽略的 `.pytest_tmp` 后验证通过；这是执行环境权限问题，不是业务测试失败。

本地合并到 `main` 后再次执行：

```powershell
python -m pytest -m "not live" -q
python -m compileall -q src tests
git diff --exit-code develop main
```

结果：测试通过，`49 passed, 1 skipped, 3 deselected`；编译检查通过；合并后的文件树与
`develop` 一致。

SupportOps 演进文档完成后执行：

```powershell
Select-String -Path SUPPORTOPS_EVOLUTION_PLAN.md `
  -Pattern 'TBD','TODO','implement later','fill in','待定','稍后实现' -SimpleMatch
git diff --check
python -m pytest -m "not live" -q
python -m compileall -q src tests
```

结果：文档无占位符，八个阶段齐全，Markdown 代码围栏成对；`git diff --check` 通过；
回归测试 `49 passed, 1 skipped, 3 deselected`；编译检查通过。

Phase 1 工单状态机与仓库切片完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase1-final -p no:cacheprovider
python -m compileall -q src tests
git diff --check
```

结果：回归测试 `89 passed, 1 skipped, 3 deselected`；编译检查和差异格式检查通过。

Phase 1 剩余领域关系完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase1-investigation-full -p no:cacheprovider
python -m compileall -q src tests
git diff --check
```

结果：回归测试 `99 passed, 1 skipped, 3 deselected`；编译检查和差异格式检查通过。

Phase 2 工单创建、列表与详情 API 完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase2-ticket-api-full -p no:cacheprovider
python -m compileall -q src tests
git diff --check
```

结果：回归测试 `105 passed, 1 skipped, 3 deselected`；编译检查和差异格式检查通过。

Phase 2 CSV/JSON 导入与附件上传 API 完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase2-intake-full -p no:cacheprovider
python -m compileall -q src tests
git diff --check
```

结果：回归测试 `120 passed, 1 skipped, 3 deselected`；编译检查和差异格式检查通过。

Phase 3 结构化调查引擎完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase3-final -p no:cacheprovider
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
git diff --check
```

结果：Fake LLM/Tool、结构化报告、证据引用、步数上限和失败状态测试均通过；最终全量结果见本轮 Change Log。

Phase 4 调查、审批和指标 API 完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase4-final -p no:cacheprovider
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
git diff --check
```

结果：`141 passed, 1 skipped, 3 deselected`；编译检查和差异格式检查通过。

Phase 5 React/Vite 前端底座完成后执行：

```powershell
cd frontend
npm test -- --run
npm run build

cd ..
$env:PYTHONPATH=(Resolve-Path .\src)
& 'D:\miniconda3\envs\agent\python.exe' -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase5-final -p no:cacheprovider
& 'D:\miniconda3\envs\agent\python.exe' -m compileall -q src tests
git diff --check
```

结果：前端 `2` 个测试文件、`4` 个测试通过，Vite 生产构建通过；后端
`141 passed, 1 skipped, 3 deselected`，编译检查和差异格式检查通过。浏览器插件因当前本地
目标访问策略拒绝打开 `127.0.0.1:5173`，未绕过该策略；响应式行为由 CSS 断点和组件测试覆盖。

## 9. Change Log

### Agent Update - 2026-06-15 Phase 5 完成

本轮 Agent 完成内容：

* 新增 React 19、Vite、TypeScript、Vitest、React Router 和 TanStack Query 前端工程。
* 新增 SupportOps 应用 Shell、编号主导航、路由占位页和无伪造数据的 Ticket Queue 空状态。
* 按概念图实现暖工程纸、近黑墨色、警示橙、硬边框、偏移阴影和等宽标识的设计 token。
* 新增 typed API client、稳定后端错误体映射、SupportOps API 契约与查询客户端默认策略。
* 新增路由可访问名称、API 成功/失败路径测试和移动端导航断点；未提前实现 Phase 6 三栏工作台。
* 浏览器插件因本地目标访问策略拒绝打开开发服务器，未使用其他浏览器通道规避；组件测试和生产构建均通过。
* 最终前端结果为 `4 passed` 且生产构建通过；后端回归为 `141 passed, 1 skipped, 3 deselected`。
* 下一步领取 Phase 6：三栏核心调查工作台。

### Agent Update - 2026-06-15 Phase 5 开始

本轮 Agent 开始内容：

* Phase 4 已通过堆叠 PR #10 提交：`https://github.com/NIYAOYE/triageops-agent-Lab/pull/10`。
* 从 `codex/investigation-approval-metrics-api` 创建 `codex/frontend-foundation` 分支。
* Phase 5 后端基线为 `141 passed, 1 skipped, 3 deselected`；Node 为 `v24.15.0`，npm 为 `11.12.1`。
* 使用 Image Gen 生成完整应用 Shell 概念，并提取暖工程纸、近黑墨色、警示橙、硬边框和偏移阴影设计系统。
* 本轮只实现前端底座与占位路由，不提前实现 Phase 6 三栏调查工作台。
* 下一步按 TDD 建立 React/Vite/Vitest 工具链、Shell 路由和 typed API client。

### Agent Update - 2026-06-15 Phase 4 开始

本轮 Agent 开始内容：

* Phase 3 已通过 PR #9 提交：`https://github.com/NIYAOYE/triageops-agent-Lab/pull/9`。
* 从 `codex/structured-investigation-engine` 创建 `codex/investigation-approval-metrics-api` 分支。
* Phase 4 基线非 live 回归为 `128 passed, 1 skipped, 3 deselected`。
* 本轮只实现调查启动/恢复/重试、SSE、审批和首次诊断时间，不提前开发前端。
* 下一步按 TDD 先实现持久化调查事件、生命周期与指标仓库契约。

### Agent Update - 2026-06-15 Phase 4 完成

本轮 Agent 完成内容：

* 新增持久化调查事件表，支持按事件 ID 恢复和 SSE 重放；SSE 仅暴露脱敏工具摘要。
* 新增 `InvestigationService`，支持新工单启动、失败后复用同一调查上下文重试、运行和详情恢复。
* 退回决定保存补充要求并自动重跑同一调查；批准与编辑后批准保存完整审批历史并结束 active investigation。
* 首次 `diagnosed_at` 在退回重查后保持不变，新增中位数和线性插值 P75 诊断耗时统计。
* 新增调查启动、详情、事件 SSE、审批和 `/v1/metrics/diagnosis-time` API，并接入生产依赖装配。
* 并发/状态冲突返回稳定 `409` 错误体；缺失工单或调查返回稳定 `404` 错误体。
* 修复已批准工单重启时先写入孤立调查的问题，状态门禁现在发生在任何 session/调查写入之前。
* 最终非 live 回归为 `141 passed, 1 skipped, 3 deselected`；编译检查和 `git diff --check` 通过。
* 未开发 React 前端、RAG、自动生产修复或自动关闭工单。

### Agent Update - 2026-06-15 Phase 3 开始

本轮 Agent 开始内容：

* 阅读并核对了项目状态、演进计划、真实目录、Git 状态、最近提交和 Phase 3 相关源码。
* 从 `codex/ticket-import-attachments` 创建 `codex/structured-investigation-engine` 分支。
* 确认本轮只实现 Phase 3 结构化调查引擎，不提前开发调查 API、SSE、审批、指标或前端。
* 使用当前工作区 `src/` 和 `agent` 环境建立基线，非 live 回归为 `120 passed, 1 skipped, 3 deselected`。
* 下一步按 TDD 先补调查结果状态、结构化输出和失败路径测试，再实现最小代码。

### Agent Update - 2026-06-15 Phase 3 完成

本轮 Agent 完成内容：

* 新增专用调查提示词和严格 Pydantic 输出契约，要求报告引用的证据键真实存在且禁止额外字段。
* 新增 `InvestigationRunner`，装配当前工单、附件和补充要求上下文，并复用现有 LangGraph 工具循环。
* 将成功工具调用保存为工具审计，校验工具结果、网页 URL 和附件归属后再整批持久化证据。
* 保存结构化 `DiagnosisReport`，成功时同步调查与工单到 `AWAITING_REVIEW`，失败时保存稳定 stop reason 并同步到 `FAILED`。
* 工具步数上限和无效证据路径会保留已经完成的工具审计，但不会留下半截证据或诊断报告。
* 新增真实 Agent 图配合 Fake LLM/Tool 的确定性测试，以及仓库状态、伪造来源、失败工具和步数上限回归测试。
* 未新增 Phase 4 API、SSE、审批或指标，也未开发 RAG、自动生产修复或自动关闭工单。
* 最终非 live 回归为 `128 passed, 1 skipped, 3 deselected`；编译检查和 `git diff --check` 通过。

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

### Agent Update - 2026-06-15 05:33

本轮 Agent 开始内容：

* 核对 `PROJECT_STATUS.md`、`SUPPORTOPS_EVOLUTION_PLAN.md`、真实目录、Git 状态、最近提交和现有 SQLite 实现。
* 确认本轮唯一任务为 Phase 1 的首个切片：工单状态机与 SQLite 工单仓库的最小模型和持久化。
* 创建 `codex/ticket-domain-foundation` 分支，不触碰未跟踪的 `agent.db-shm` 与 `agent.db-wal`。
* 基线非 live 测试通过：`49 passed, 1 skipped, 3 deselected`。
* 下一步按 TDD 先实现状态机，再实现工单仓库；不修改现有聊天 API。

### Agent Update - 2026-06-15 05:37

本轮 Agent 完成内容：

* 新增不可变 `Ticket` 模型，以及优先级、来源和六状态枚举。
* 实现计划定义的七条合法状态迁移；非法迁移返回稳定领域错误且不会污染持久化状态。
* 新增独立 `SQLiteTicketRepository`，支持创建、读取、跨重启恢复和受状态机保护的状态更新。
* 使用失败测试驱动实现，新增 40 个状态机与仓库测试，穷举全部状态转换；没有修改现有聊天服务和 API。
* 非 live 回归测试通过：`89 passed, 1 skipped, 3 deselected`；编译检查和 `git diff --check` 通过。
* 下一子任务应继续 Phase 1，补齐附件、调查、证据、诊断和审批模型及仓库关系，不进入 Phase 2 API。

### Agent Update - 2026-06-15 05:43

本轮 Agent 开始内容：

* 将 `codex/ticket-domain-foundation` 推送到 `origin`，远端分支已建立并配置跟踪。
* 从已推送提交创建 `codex/ticket-investigation-domain` 分支。
* 本轮唯一任务是完成 Phase 1 剩余领域模型及 SQLite 关系，不实现附件上传 API、调查 Runner 或审批 API。
* 计划按 TDD 固定外键、单工单唯一 active investigation、证据类型约束、报告证据归属和审批历史。

### Agent Update - 2026-06-15 05:49

本轮 Agent 完成内容：

* 新增附件、调查、证据、诊断报告和审批不可变领域模型。
* 扩展 SQLite 迁移与仓库，建立工单、会话、工具审计、附件和调查之间的外键关系。
* 使用部分唯一索引保证每张工单最多一个未完成调查，并提供稳定冲突错误。
* 校验工具证据属于调查会话、附件证据属于调查工单、网页证据保留 URL。
* 诊断报告仅能引用当前调查证据，保留证据顺序、置信度、建议步骤和回复草稿；审批保留完整历史。
* 新增 10 个领域关系测试；全量非 live 回归为 `99 passed, 1 skipped, 3 deselected`。
* Phase 1 已完成；下一轮应进入 Phase 2 工单接入 API，不开发 RAG、调查 Runner 或自动生产修复。

### Agent Update - 2026-06-15 05:54

本轮 Agent 开始内容：

* 将 `codex/ticket-investigation-domain` 推送到 `origin`，远端分支已建立并配置跟踪。
* 从已推送提交创建 `codex/ticket-read-api` 分支。
* 本轮唯一任务为 Phase 2 的手动创建、分页筛选列表和详情 API；导入与附件上传留给后续切片。
* 基线非 live 回归通过：`99 passed, 1 skipped, 3 deselected`。
* 新增薄 `TicketService` 承担工单用例编排，不向现有 `ChatService` 混入工单逻辑。

### Agent Update - 2026-06-15 05:58

本轮 Agent 完成内容：

* 新增 `TicketService`，提供手动创建、分页筛选排序和详情用例编排。
* 扩展 SQLite 工单仓库，支持状态与优先级筛选、分页总数、白名单排序和当前调查查询。
* 新增 `POST /v1/tickets`、`GET /v1/tickets` 和 `GET /v1/tickets/{id}`。
* 新工单接口为重复 ID 和缺失工单返回带 request ID 的稳定 `409/404` 错误体。
* 保持 `create_app(service)` 与现有聊天 API 兼容；生产装配在同一数据库上注入独立工单服务。
* 新增 6 个服务与 API 测试；全量非 live 回归为 `105 passed, 1 skipped, 3 deselected`。
* Phase 2 尚未完成；下一子任务是 CSV/JSON 导入与受控附件上传 API。

### Agent Update - 2026-06-15 06:01

本轮 Agent 开始内容：

* 将 `codex/ticket-read-api` 推送到 `origin`，远端分支已建立并配置跟踪。
* 从已推送提交创建 `codex/ticket-import-attachments` 分支。
* 本轮唯一任务为 CSV/JSON 原子导入与受控附件上传 API，不进入调查 Runner 或 Phase 3。
* 导入采用整批校验、零部分写入；附件采用扩展名、媒体类型、文本特征、单文件和单工单总量限制。

### Agent Update - 2026-06-15 06:10

本轮 Agent 完成内容：

* 新增 multipart `POST /v1/tickets/import`，支持 UTF-8/GB18030 CSV 与 JSON 数组导入。
* 导入在写入前校验表头、必填字段、优先级、空批次、重复 ID 和文件大小，任一错误均零部分写入。
* 新增 `POST /v1/tickets/{id}/attachments`，仅允许 `.log`、`.txt`、`.csv`、`.json` 文本附件。
* 附件校验扩展名、媒体类型、编码、空字节和 JSON 内容特征，并使用工单 ID 哈希隔离存储目录。
* 增加单文件和单工单累计大小限制，以及稳定的 `400/404/413` 错误体。
* 声明 `python-multipart==0.0.32` 和 `AGENT_MAX_TICKET_ATTACHMENT_BYTES` 配置。
* 新增 15 个导入与附件测试；全量非 live 回归为 `120 passed, 1 skipped, 3 deselected`。
* Phase 2 已完成；下一轮应进入 Phase 3 结构化调查 Runner，不开发 RAG 或自动生产修复。

### Agent Update - 2026-06-15 08:23

本轮 Agent 完成内容：

* 将项目对外名称更新为 `TriageOps Agent Lab`，并同步新的 GitHub 仓库链接。
* 按 Phase 2 真实进度重写 README，补充架构、模块、工单 API、导入、附件、安全边界和后续路线。
* 所有公开命令使用通用 Python 命令、环境变量和仓库相对路径，不包含本机绝对路径或真实密钥。
* 非 live 回归测试通过：`120 passed, 1 skipped, 3 deselected`；编译检查和文档格式检查通过。
