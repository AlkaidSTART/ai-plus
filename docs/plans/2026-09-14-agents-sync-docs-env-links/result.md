# 新增需求偏差同步文档与外部访问链接环境变量规则：实施结果

## 完成状态
已完成。已按获批计划修改 `AGENTS.md`，并完成文本范围与格式检查。

## 实际变更
- 修改 `AGENTS.md`：
  - 将 `## Four Principles` 更新为 `## Five Principles`。
  - 新增 `### 5. 需求偏差同步文档，外部访问链接配置化`。
  - 新规则明确：已确认的实际需求和已验证实现是调整依据，文档不是唯一依据；实质性偏差须先修订 `plan.md` 并重新获批；获批后同步更新受影响文档；不得虚构实现迎合文档。
  - 新规则明确：运行时访问外部服务的链接（例如亚马逊官网地址）不得硬编码，必须通过环境变量提供并由项目配置层读取；同步维护环境变量示例文件中的变量名和非敏感占位值，不提交真实密钥或环境专属值；静态文档引用超链接不适用。
- 新增 `docs/plans/2026-09-14-agents-sync-docs-env-links/result.md`，用于单独记录本次实施和验证结果。
- 未修改代码、配置、`README.md`、`PRD.md`、现有设计/API 文档或环境变量文件。

## 实施记录
1. 只读检查了现行 `AGENTS.md` 中的文档冲突规则、四项原则和任务审批/结果约束，确认新增规则应位于第 4 条原则之后。
2. 用户以“开始”明确批准 `plan.md`；该批准信息和日期已记录在计划的“审核状态”中。
3. 将原则章节标题改为 `## Five Principles`。
4. 在第 4 条原则与 `## 任务计划与结果记录（强约束）` 之间插入第 5 条规则，未改动其他章节。
5. 重新读取相关区段，并执行标题、关键约束、差异范围和空白格式检查。
6. 验证通过后新增本 `result.md`，未将实施结果混写回 `plan.md`。

本任务为单文件、精确文本插入，没有可独立并行且不重叠的实施或验证工作包，因此未使用子代理。

## 验证命令与真实结果
- `rg -n '^## Five Principles$|^### 5\\. 需求偏差同步文档，外部访问链接配置化$' AGENTS.md`
  - 退出码：`0`
  - 结果：命中 `AGENTS.md:32` 和 `AGENTS.md:64`。
- `rg -n '文档不是唯一依据|同步更新受影响的文档|不得硬编码|必须通过环境变量|亚马逊官网' AGENTS.md`
  - 退出码：`0`
  - 结果：关键约束均命中，包括 `AGENTS.md:68`、`AGENTS.md:70` 和 `AGENTS.md:73`。
- `git diff --check -- AGENTS.md`
  - 退出码：`0`
  - 结果：无输出，未发现空白格式错误。
- `git diff --stat -- AGENTS.md`
  - 结果：`1 file changed, 12 insertions(+), 1 deletion(-)`。
- `git diff -- AGENTS.md`
  - 结果：仅显示 `Four Principles` 改为 `Five Principles`，以及新增第 5 条规则；没有其他章节或文件内改动。
- `git hash-object AGENTS.md`
  - 结果：修改后 blob 为 `b544f2e04681a120cabb59d55e6b805c6e272661`；`git diff` 显示修改前 blob 为 `a7f7a1f991d094b77a4247a9d2efde8382197efe`。
- `git status --short`
  - 本任务产生：`M AGENTS.md` 和本任务计划目录。
  - 工作树同时存在非本任务改动：`backend/pyproject.toml`、`backend/uv.lock`、`docs/plans/2026-09-14-backend-dependencies/`；本次未读写或修改这些内容。

补充记录：首次包装 `git diff --check` 的命令尝试使用 zsh 的只读特殊参数 `status` 保存退出码，导致外层包装命令失败；`git diff --check` 本体并未因此修改文件。随后改用变量名 `rc` 重跑，退出码为 `0`。

## 计划偏差
无实质性偏差。实际修改文件、规则位置、规则内容和验证范围均符合获批计划；补充记录了一处验证包装命令的变量命名失败及修正过程。

## 遗留问题与未执行检查
- 本次只新增仓库规则，未排查或迁移现有源码中的硬编码外部访问链接。
- 本次未新增或填写任何环境变量，也未修改环境变量示例文件。
- `backend/pyproject.toml`、`backend/uv.lock` 和 `docs/plans/2026-09-14-backend-dependencies/` 的改动不属于本任务，未纳入本次验证范围或结果。
- 未执行 commit、push、PR、部署或其他外部状态变更。
