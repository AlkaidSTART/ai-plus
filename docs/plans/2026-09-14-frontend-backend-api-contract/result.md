# 前后端接口清单与契约草案：实施结果

## 完成状态

已完成。

本次任务按已批准的 `plan.md` 交付了前后端接口清单与 P0 契约草案，未实现任何接口、未修改前后端代码，也未生成正式 OpenAPI 或事件 schema。

## 实际变更

- 新增 `docs/api.md`，共 718 行，覆盖：
  - 文档性质、权威顺序与成熟度图例；
  - 通用 HTTP、JSON 命名、响应信封、认证租户、分页与幂等约定；
  - 当前唯一已实现接口 `GET /api/v1/health`；
  - 8 个 P0 拟议任务接口及其请求、响应、状态和错误语义；
  - `Page<T>`、`TaskCreateRequest`、`TaskCreatedResponse`、`TaskListItem`、`TaskSnapshot`、`TaskItemSnapshot`、`SampleMetrics`、`NodeProgress`、`Report`、`Evidence` 等共享 DTO；
  - 任务、数据质量、财务、节点四类状态；
  - SSE 连接行为、事件信封和三个 P0 事件；
  - P1/P2 能力边界、历史 `/api/v1/insight/...` 说明、待确认决策、契约演进规则和依据索引。
- 更新 `docs/plans/2026-09-14-frontend-backend-api-contract/plan.md`，记录已批准状态及用户批准原文“开始”。
- 新增本文件 `docs/plans/2026-09-14-frontend-backend-api-contract/result.md`。

## 实施记录

1. 只读核对后端健康接口、路由、测试、正式架构文档、PRD、前端 SSE 草案和新建任务草案，确认当前仅有 `GET /api/v1/health` 有实现证据。
2. 按批准计划编写接口盘点与契约草案，将代码事实、正式目标、拟议契约和历史资料分开标注。
3. 独立复核发现并补齐分页泛型、样本统计指标、痛点量化字段、建议双栏与证据约束、认证方向及 SSE 数据质量语义。
4. 独立复核代理进行增量只读复核，结论为“通过，无阻断问题”；唯一非阻断提示是表格内联枚举中的 `|` 可能被严格 Markdown 渲染器误拆列。随后将该处改为斜杠分隔的独立行内代码写法，不改变枚举含义。
5. 对交付文档执行结构、路径、状态和关键契约断言，全部通过。

## 验证命令与真实结果

- `wc -l docs/api.md`
  - 结果：`718 docs/api.md`。
- Python 契约断言脚本
  - 检查 Markdown 文件末尾换行、代码围栏配对、尾随空白、9 个方法/路径组合、8 个 P0 任务接口、关键 DTO/SSE 字段、实现状态及历史路径位置。
  - 结果：`lines=718 fences=28 trailing_whitespace=0 final_newline=yes`；`required_method_paths=9 p0_task_rows=8 insight_history_lines=[667, 668, 669, 670, 671, 672]`；`contract_assertions=passed`。
- `git diff --check -- docs/api.md docs/plans/2026-09-14-frontend-backend-api-contract/`
  - 结果：无输出、退出码 0。
  - 说明：`docs/api.md` 当前为未跟踪文件，该命令不会检查其全部内容；该文件的尾随空白和最终换行由上述 Python 脚本直接检查。
- `git status --short`
  - 结果：本次任务产生 `M docs/plans/2026-09-14-frontend-backend-api-contract/plan.md`、`?? docs/api.md` 和本结果文件；未提交、推送或创建 PR。
- 独立复核
  - 结果：增量只读复核通过，无阻断问题；确认 8 个任务接口均标为“P0 拟议-未实现”，历史 `/api/v1/insight/...` 仅位于历史说明，DTO 和 SSE 修正已生效。

首次和第二次 Python 检查脚本分别因路径匹配方式过于字面、漏引入 `re` 而产生误报；修正检查脚本后，上述最终断言通过。误报不涉及 `docs/api.md` 内容变更。

## 计划偏差

- 无实质性偏差。
- 在批准范围内补充分页泛型、样本统计、痛点量化、建议栏目与证据约束等 DTO 细节。
- 为 Markdown 渲染兼容性，移除了两处尾随空格，并将两个内联枚举的 `|` 改为斜杠分隔；均不改变契约含义。
- 未修改任何代码、配置、依赖、测试或正式契约文件。

## 遗留问题与未执行检查

- `docs/api.md` 仍是评审草案，不是机器可依赖的最终契约；后端 Pydantic DTO、OpenAPI、事件 schema 和前端生成客户端尚未实现。
- 待后端确认的关键事项包括 JSON 命名、成功/错误信封、认证与 CSRF 细节、幂等 header、多项目语义、节点状态枚举、重试模型、SSE 保留策略和模型元数据结构。
- 因本任务只新增文档，未执行接口集成测试、前后端联调、OpenAPI 校验或事件 schema 校验。
