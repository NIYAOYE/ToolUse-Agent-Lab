# Project Status

## 1. Project Goal

将现有不依赖 RAG 的 Tool-Use Agent 演进为 SupportOps 工单调查工作台：面向研发与运维
技术支持工程师，使用 Qwen、Tavily、受限文件读取和受限 Python 分析工单，生成带证据的
结构化诊断方案，由人工审批，并以首次诊断时间衡量效率。

## 2. Current Architecture

主要调用链为：CLI/HTTP 请求 -> FastAPI -> `ChatService` -> LangGraph Agent -> Qwen
Function Calling -> 工具注册中心 -> Tavily / 文件读取 / Python 执行 / 日志扫描 / JSON 查询 / CSV 概览。会话消息、历史摘要和
工具审计记录由 SQLite 仓库持久化，`composition.py` 负责从环境变量读取配置并装配运行时依赖。

当前架构已在 Agent 内核外提供 React 工单工作台、工单领域模型、`TicketService`、
`InvestigationService`、结构化诊断报告、证据链、人工审批、诊断耗时指标与完整审计视图。
FastAPI 入口还提供受控 Host/CORS、请求 ID 和不记录敏感正文的结构化请求日志。
完整设计与阶段边界见 `SUPPORTOPS_EVOLUTION_PLAN.md`。

## 3. Completed Work

- [x] 项目配置、环境变量读取与 Qwen 客户端
- [x] Tavily 网页搜索工具与统一工具注册中心
- [x] 工作目录内的受限文件读取工具
- [x] 基于 AST、隔离进程、超时和输出限制的 Python 执行工具
- [x] SupportOps 附件分析工具：日志扫描、JSON 查询和 CSV 概览
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
- [x] 完成 Phase 6：三栏调查工作台、真实工单/调查查询、证据诊断展示和人工决策
- [x] 完成 Phase 7：原子导入页面、首次诊断时间看板和完整调查审计详情
- [x] 完成 Phase 8：演示数据、真实 API 演示、部署说明、结构化日志和安全边界文档
- [x] 完成前端中英文语言切换，并通过 PR #16 合入远端 `main`

## 4. In Progress

- 当前无正在开发的 SupportOps 阶段任务；前端语言切换 PR #16 已合并。

## 5. TODO / Next Steps

- [ ] 按后续计划继续领取下一项未完成的 SupportOps 任务

## 6. Known Issues

- `python_exec` 适合本地演示和半可信输入，不是可安全执行恶意代码的生产级沙箱。
- HTTP API 当前没有认证和限流，不应直接暴露到公网。
- 真实 API 冒烟测试会消耗 Qwen 与 Tavily 配额，默认测试流程不会自动执行这些用例。
- 远端 `main` 启用了“必须通过 Pull Request 修改”的保护规则，不能直接 `git push main`。
- 2026-06-15 推送 Phase 5 分支及运行 Phase 8 live 测试时，Codex 外部授权服务曾达到用量上限；
  2026-06-16 使用 `agent` conda 环境和提权网络完成 Phase 8 live 验收，并补齐 Phase 5-8 PR。
- 普通沙箱运行真实 API 仍会因外网权限报 `WinError 10013`；live 验收必须使用显式提权网络执行。
- MVP 不包含 RAG、自动执行生产修复、自动关闭工单或真正的多 Agent 运行时。
- `agent` 环境的可编辑安装可能指向其他 worktree；验证当前工作区代码时可显式设置
  `PYTHONPATH` 为仓库内的 `src/`，或重新安装当前工作区。

## 7. Important Files

| File / Directory | Purpose |
| --- | --- |
| `src/tool_use_agent/agent/` | LangGraph 状态、提示词和工具调用循环 |
| `src/tool_use_agent/tools/` | Tavily、文件读取、Python 执行、日志扫描、JSON 查询、CSV 概览和工具注册 |
| `src/tool_use_agent/memory/` | SQLite 数据模型与持久化仓库 |
| `src/tool_use_agent/llm/` | Qwen 客户端和历史摘要器 |
| `src/tool_use_agent/service.py` | 多轮会话、历史压缩和工具审计编排 |
| `src/tool_use_agent/api/` | FastAPI 路由、请求模型与 SSE 编码 |
| `src/tool_use_agent/api/tickets.py` | 工单创建、列表、详情路由与稳定错误体 |
| `src/tool_use_agent/composition.py` | 配置读取和运行时依赖装配 |
| `src/tool_use_agent/cli.py` | HTTP/SSE 终端客户端 |
| `src/tool_use_agent/demo.py` | 四条合成演示工单的幂等种子命令 |
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
| `frontend/src/i18n.tsx` | 前端中英文语言状态、翻译字典和本地持久化 |
| `frontend/src/pages/InvestigationWorkbenchPage.tsx` | 三栏队列、调查时间线、证据、诊断报告和人工审批工作台 |
| `frontend/src/pages/TicketQueuePage.tsx` | 真实工单分页响应的队列入口与工单选择 |
| `frontend/src/InvestigationWorkbench.test.tsx` | 选中工单、启动调查、编辑回复和批准诊断的组件集成流程 |
| `frontend/src/pages/ImportTicketsPage.tsx` | CSV/JSON multipart 原子导入界面与边界说明 |
| `frontend/src/pages/MetricsPage.tsx` | 首次诊断样本数、Median 和 P75 看板 |
| `frontend/src/pages/AuditPage.tsx` | 工具参数/结果、事件、证据和人工决策只读审计详情 |
| `src/tool_use_agent/api/investigations.py` | 调查、SSE、审计、审批和诊断耗时路由 |
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
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase3-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：Fake LLM/Tool、结构化报告、证据引用、步数上限和失败状态测试均通过；最终全量结果见本轮 Change Log。

Phase 4 调查、审批和指标 API 完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase4-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
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
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase5-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：前端 `2` 个测试文件、`4` 个测试通过，Vite 生产构建通过；后端
`141 passed, 1 skipped, 3 deselected`，编译检查和差异格式检查通过。浏览器插件因当前本地
目标访问策略拒绝打开 `127.0.0.1:5173`，未绕过该策略；响应式行为由 CSS 断点和组件测试覆盖。

Phase 6 三栏核心调查工作台完成后执行：

```powershell
cd frontend
npm test -- --run
npm run build

cd ..
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase6-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：前端 `3` 个测试文件、`6` 个测试通过，覆盖选中工单到批准诊断以及启动调查请求；
Vite 生产构建通过。后端 `141 passed, 1 skipped, 3 deselected`，编译检查和差异格式检查通过。
计划中的 Playwright 本地主流程因浏览器插件的本地目标访问策略无法执行，未使用其他浏览器通道规避；
同一主流程由 Testing Library + jsdom 的组件集成测试验证。

Phase 7 导入、指标和审计视图完成后执行：

```powershell
cd frontend
npm test -- --run
npm run build

cd ..
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase7-full -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：前端 `4` 个测试文件、`9` 个测试通过，Vite 生产构建通过；后端新增工具审计详情
API 测试后为 `142 passed, 1 skipped, 3 deselected`，编译检查和差异格式检查通过。

Phase 8 演示与运行时硬化完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase8-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests

cd frontend
npm test -- --run
npm run build
```

结果：后端 `148 passed, 1 skipped, 4 deselected`，前端 `4` 个测试文件、`9` 个测试通过，
Vite 生产构建和 Python 编译通过。种子命令首次运行返回 `{"created":4,"existing":0}`，
再次运行返回 `{"created":0,"existing":4}`。

2026-06-16 继续收尾时，按用户要求使用 `agent` conda 环境重新验证：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\phase8-conda-final -p no:cacheprovider
conda run -n agent python -m compileall -q src tests

cd frontend
npm test -- --run
npm run build
```

结果：后端 `148 passed, 1 skipped, 4 deselected`；Python 编译和 `git diff --check` 通过；
前端 `4` 个测试文件、`9` 个测试通过；Vite 生产构建通过。

Phase 8 live 验收执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
$env:PYTHONIOENCODING="utf-8"
conda run --no-capture-output -n agent python -m pytest tests/live/test_live_smoke.py `
  -m live -q -s --basetemp .pytest_tmp\phase8-live-conda-2 -p no:cacheprovider
```

结果：提权网络下 `4 passed in 19.76s`。首次提权运行中前两个 live 用例已通过，后两个用例被旧
`.pytest_tmp\phase8-live-conda` 目录清理权限阻塞；改用新的 basetemp 后完整通过。

前端中英文语言切换功能完成后执行：

```powershell
cd frontend
npm test -- --run
npm run build

cd ..
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\i18n-nonlive -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：前端 `4` 个测试文件、`10` 个测试通过；Vite 生产构建通过；后端非 live
`148 passed, 1 skipped, 4 deselected`；Python 编译和差异格式检查通过。

SupportOps 工具函数增强完成后执行：

```powershell
$env:PYTHONPATH=(Resolve-Path .\src)
conda run -n agent python -m pytest -m "not live" -q `
  --basetemp .pytest_tmp\utility-tools -p no:cacheprovider
conda run -n agent python -m compileall -q src tests
git diff --check
```

结果：后端非 live 回归通过，`154 passed, 1 skipped, 4 deselected`；Python 编译检查和差异格式检查通过。

## 9. Change Log

### Agent Update - 2026-06-16 SupportOps 工具函数增强

本轮 Agent 完成内容：
* 按 TDD 新增 `log_scan`、`json_query` 和 `csv_profile` 三个受控工作区文本分析工具。
* 新增共享工作区文本读取 helper，统一相对路径、越界、二进制、编码和大小限制边界。
* 将新工具注册到 `composition._build_registry_and_model()`，聊天服务和调查服务都会向 Qwen Function Calling 暴露同一组工具 schema。
* 新增工具单元测试和运行时装配测试；保持 LangGraph 主循环、调查 Runner、API、数据库和前端架构不变。
* 同步更新 `README.md`、`SUPPORTOPS_EVOLUTION_PLAN.md` 和本状态文档；未引入 RAG、自动生产修复或外部工单系统对接。
* 验证结果：后端非 live `154 passed, 1 skipped, 4 deselected`，Python 编译和 `git diff --check` 通过。

### Agent Update - 2026-06-16 前端语言切换

本轮 Agent 完成内容：

* 从 `codex/demo-hardening` 创建 `codex/frontend-language-toggle` 分支，保留已有 SQLite WAL 临时文件未跟踪。
* 按 TDD 先新增语言切换测试，确认缺少“中文”按钮时失败，再实现功能。
* 新增轻量 `I18nProvider`、中英文字典、`useI18n()` 和 localStorage 语言持久化，默认英文。
* 在 Shell 右上角新增 `English / 中文` 切换控件，并翻译导航、页脚、状态徽标、Tickets、Import、Metrics、Audit、占位页和调查工作台固定文案。
* 工单标题、诊断内容、工具审计 JSON 等后端数据保持原文，不做自动翻译。
* 验证结果：前端 `10 passed`，Vite 构建通过；后端非 live `148 passed, 1 skipped, 4 deselected`，编译和差异检查通过。
* PR #16 已创建并合并到远端 `main`：`https://github.com/NIYAOYE/triageops-agent-Lab/pull/16`。

### Agent Update - 2026-06-16 Phase 8 验收完成

本轮 Agent 完成内容：

* 核对当前分支为 `codex/demo-hardening`，Phase 8 实现提交为 `65c61d0`，除 SQLite WAL 临时文件外无未提交源码。
* 按用户要求使用 `conda run -n agent` 验证 Python 代码。
* 非 live 回归重新通过：后端 `148 passed, 1 skipped, 4 deselected`，Python 编译和 `git diff --check` 通过。
* 前端测试与构建按顺序通过：`9 passed`，Vite 生产构建通过。
* 普通沙箱 live 测试仍被 `WinError 10013` 拦截；提权网络后完整 live 验收通过：`4 passed in 19.76s`。
* `conda run` 默认捕获输出时曾因 GBK 编码触发 `UnicodeEncodeError`；改用 `--no-capture-output` 后正常执行。
* 补推 Phase 4-8 远端分支，确认 Phase 4 PR #10、Phase 5 PR #11、Phase 6 PR #12、Phase 7 PR #13 已合并。
* 创建并更新 Phase 8 PR #14：`https://github.com/NIYAOYE/triageops-agent-Lab/pull/14`。
* 创建最终集成 PR #15：`https://github.com/NIYAOYE/triageops-agent-Lab/pull/15`，用于将 Phase 7/8 结果合入受保护 `main`。

### Agent Update - 2026-06-16 删除工单与 README 展示刷新

本轮 Agent 完成内容：

* 新增 `DELETE /v1/tickets/{id}`，删除工单时复用 SQLite 外键级联清理调查、证据、报告、审批和事件记录。
* `TicketService.delete_ticket()` 会在数据库删除后清理该工单上传到工作区的附件文件，并移除空附件目录。
* React 工单队列新增删除按钮，删除前使用浏览器确认框，成功后刷新队列。
* README 改为中文主文案的 GitHub 展示版，保留专有技术名词英文；预留截图路径 `assets/triageops-workbench.png`。
* 新增 `assets/README.md`，说明手动截图命名和放置位置。
* 复用并纳入 `sample_data/supportops/` 合成工单与附件，便于本地导入和工具函数演示。
* 验证结果：后端非 live `157 passed, 1 skipped, 4 deselected`，Python 编译通过；前端 `11 passed`，Vite 生产构建通过。

### Agent Update - 2026-06-15 Phase 8 本地实现完成

本轮 Agent 完成内容：

* 从 Phase 7 提交创建 `codex/demo-hardening`，只实现 Phase 8 演示、部署和安全硬化范围。
* 新增四条纯合成工单及幂等 `supportops-seed` 命令，不重复写入，也不会自动启动调查。
* 新增环境变量控制的 Trusted Host 与 CORS 白名单，默认仅允许本机 API 和 Vite 开发来源。
* 新增请求 ID 与单行 JSON 请求日志；日志不记录 query string、正文、附件和 API Key。
* 补齐真实部署说明，明确反向代理应承担 TLS、认证、限流，SQLite 仅用于单实例演示。
* 新增真实 SupportOps live 用例，覆盖工单创建、Qwen/Tavily 调查、证据校验与人工批准。
* 非 live 最终结果为后端 `148 passed, 1 skipped, 4 deselected`、前端 `9 passed`，生产构建和编译通过。
* live 用例和 Phase 5-8 远端推送当时受 Codex 外部授权额度阻塞；2026-06-16 已继续完成 live 验收。

### Agent Update - 2026-06-15 Phase 7 完成

本轮 Agent 完成内容：

* 从 Phase 6 提交创建 `codex/import-metrics-audit-views`，只实现 Phase 7 交付范围。
* 新增 CSV/JSON multipart 导入页，明确原子校验、重复 ID、文件大小和不会自动启动调查的边界。
* 新增首次诊断时间看板，直接展示后端计算的诊断样本数、Median 和 P75，不生成伪造指标。
* 新增只读工具审计 API，按调查 session 返回工具名、调用 ID、完整参数、结果和创建时间。
* 新增完整审计页，展示工具输入/输出、调查事件 payload、证据账本和人工审批最终稿。
* 在三栏工作台增加当前调查的 Audit 入口；未增加自动执行建议或生产修复按钮。
* 新增导入 multipart、指标呈现、完整审计展示和缺失调查错误测试；最终前端 `9 passed`，
  后端 `142 passed, 1 skipped, 3 deselected`，生产构建、编译和差异检查通过。
* 下一步领取 Phase 8：演示数据、真实 API 验证和安全硬化。

### Agent Update - 2026-06-15 Phase 7 开始

本轮 Agent 开始内容：

* Phase 6 本地提交为 `2ea0d0c`，Phase 5/6 远端推送仍等待 Codex 外部授权额度恢复。
* 从 `codex/investigation-workbench` 创建 `codex/import-metrics-audit-views`。
* 检查真实后端后确认缺少完整工具审计读取 API，因此先按 TDD 补只读契约，再实现三个前端视图。
* 本阶段不提前创建 Phase 8 演示数据，不运行真实付费 API，也不开发 RAG 或自动生产修复。

### Agent Update - 2026-06-15 Phase 6 完成

本轮 Agent 完成内容：

* 从 Phase 5 提交创建 `codex/investigation-workbench`，只实现 Phase 6 核心工作台。
* Ticket Queue 改为读取真实分页 API，展示优先级、服务、状态、更新时间并提供可访问的工单入口。
* 新增三栏工作台：左栏工单队列与上下文，中栏调查时间线与证据，右栏结构化诊断与人工审批。
* 支持带补充要求启动/重试调查，以 1.5 秒间隔刷新活动调查，并在终态自动停止刷新。
* 支持编辑最终回复后批准、原稿批准和附审阅意见退回重查；未提供任何自动生产修复入口。
* 修复切换工单时临时调查状态残留，并提供启动、加载和决策失败的可见错误反馈。
* 新增主流程组件集成测试；最终前端 `6 passed`、生产构建通过，后端回归保持
  `141 passed, 1 skipped, 3 deselected`。
* Playwright 因浏览器本地目标策略被阻止，未绕过；下一步领取 Phase 7 导入、指标和审计视图。

### Agent Update - 2026-06-15 Phase 6 开始

本轮 Agent 开始内容：

* Phase 5 本地提交为 `0a7df51`；远端推送因 Codex 外部授权额度限制暂时被拒绝。
* 从 `codex/frontend-foundation` 创建 `codex/investigation-workbench`。
* 按 TDD 先新增“队列选中工单 -> 展示证据与诊断 -> 编辑回复 -> 人工批准”的失败测试。
* 本阶段不开发 Phase 7 导入、指标和审计详情，也不增加 RAG 或自动生产修复能力。

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
