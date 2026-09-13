# Monorepo、技术选型与云端模型文档修订结果

## 1. 完成状态

- **已完成：R1 获批文档修订、验证与独立结果记录。** 本任务不代表前后端、云模型、数据库或部署已经实现。
- 实施依据：[plan.md](plan.md) 的 R1 云端方案；用户在修订版展示后明确回复 **“确定”**，真实批准信息已记录在计划第 11 节。
- 日期：2026-09-12。文档复核命令输出为 `2026-09-12 16:19:27 +0800`；不将本机时间冒充用户消息时间戳。
- 本次仅改设计文档、审批记录并生成本结果文件；没有创建脚手架、安装依赖、采集数据、调用收费模型、执行迁移、暂存、提交或部署。

## 2. 实际变更

| 文件 | 实际内容 |
| --- | --- |
| [docs/architecture.md](../../architecture.md) | 新增 V1.0 正式目标架构：轻量 monorepo、前后端选型、模块边界、Celery/Redis/outbox、LangGraph 持久恢复、生成契约与 SSE、云端模型/向量/证据、安全、部署和分层验证；整理 24 组官方参考并保留证据限制 |
| [PRD.md](../../../PRD.md) | 定向修订为 V1.2：统一三类云端模型、P0/P1/P2、样本与证据口径、真实状态/财务未评估、数据流与概念状态模型、安全和 NFR 测量条件、MVP 范围及里程碑 |
| [README.md](../../../README.md) | 同步目标栈和阶段边界，明确当前只有设计文档；移除缺失代码的启动命令、501 实现断言及失效文档入口 |
| `plan.md` | 记录 R1 已批准状态、用户原文和实际记录日期；没有把实施结果混写进计划 |
| `result.md` | 本独立结果记录，在正式文档修订与验证后生成 |

### 关键决策已落实到文档

1. `frontend/` 与 `backend/` 分别使用 Bun/uv 及各自锁文件；API、Worker、dispatcher 共用 Python 业务包。暂不引入 workspace、Turborepo/Nx 或空共享包。
2. 前端采用 Vue 3 / TypeScript strict / Vite / Element Plus / ECharts；Vue Query 管服务端数据，Pinia 管跨页 UI 状态。
3. 后端采用 FastAPI / Pydantic / SQLAlchemy / psycopg / Alembic；Celery/Redis 与事务 outbox 承接任务，LangGraph/PostgreSQL checkpointer 承接图恢复，PostgreSQL 持久事件承接 SSE 回放。
4. **LLM、VLM、Embedding 均为云端 API**。Claude 为 LLM/VLM 方向，SiliconFlow `BAAI/bge-m3` 为 Embedding 待验证候选；不下载权重，不部署本地/自建 GPU 推理，不静默回退本地或跨供应商混用向量。
5. pgvector 负责存储/检索，CPU scikit-learn 负责聚类，云端 LLM 负责基于证据生成标签与建议；HNSW 按实测需要引入。
6. P0 为文本闭环和基础溯源，P1 才做视觉/确定性财务；P0 财务为 `NOT_EVALUATED`，最多展示 5 类有证据痛点，不以缺失数据或未执行步骤生成假结果。

## 3. 实施记录与范围保护

1. 实施前重新读取适用约定和目标文件，核验工作区、日期及保护文件哈希；收到 R1 展示后的批准后才记录审批并修改正式文档。
2. 新增英文文件名 `docs/architecture.md`，没有恢复已删除的旧技术方案、API 文档或业务实现。
3. PRD 使用定向替换；原产品愿景/目标用户、用户角色表、未涉及的 P1/P2 功能段落通过原始内容比对，10 个功能编号保留。
4. 完整回读三份正式文档；人工复核将 SSE 图示改为与工作单元执行并行的实时读取/回放，避免误解为全部任务结束后才推送。这是获批实时流程的表达修正，不是新增行为。
5. 执行差异、空白、表格/围栏、本地链接、跨文档约束、来源集合、原 PRD 保留段落及 Git 范围检查；修正后再次运行，均通过。
6. 原有 `AGENTS.md` 修改和 **127 个未暂存删除**均保留；`.gitignore`、`LICENSE` 及上一任务 plan/result 的 SHA-256 与实施前一致。没有生成运行目录、配置、锁文件或新的代码文件。

### 分工

未使用子代理：当前会话没有可直接调用的子代理工具，探索时未发现可用的 paseo CLI。由主代理负责调研整合、文档修订与验证；并行文件读取不冒充独立代理评审。

## 4. 验证命令与真实结果

工作目录：`D:/Project/ai-plus`。

| 检查 | 实际命令/方式 | 真实结果 |
| --- | --- | --- |
| 日期 | `date '+%Y-%m-%d %H:%M:%S %z'` | 输出 `2026-09-12 16:19:27 +0800` |
| 已跟踪差异与空白 | `git diff --check -- PRD.md README.md docs/architecture.md docs/plans/2026-09-12-monorepo-architecture-selection/` | 退出码 0，无空白错误；未用它代替未跟踪文件检查 |
| 全文和差异 | read 工具完整读取三份正式文档；`git diff -- README.md`；Node 读取原 PRD blob 比对 | README 的旧启动/接口/链接描述已移除；PRD 未涉及段落保持一致 |
| 文档与范围断言 | 下方 `node` stdin 脚本，不写检查脚本或临时项目文件 | 结果文件生成前：4 份文档、8 个本地链接、表格/围栏/空白、云端/技术栈/阶段口径、PRD 基线/功能编号/数值目标、图控制块、审批、24 组来源、5 个保护哈希及 127 个删除全部通过 |
| 文件指纹 | `sha256sum PRD.md README.md docs/architecture.md docs/plans/2026-09-12-monorepo-architecture-selection/plan.md` | 与下表一致 |
| 暂存与运行文件 | 断言脚本中的 `git status --porcelain=v1 -z --untracked-files=all`、`git diff --cached --exit-code --quiet` 和存在性检查 | 无暂存；本任务写入范围正确；frontend/backend/contracts/Compose/CI 未创建 |

Mermaid 检查只覆盖围栏和 `par/and/loop/alt/opt/end` 等控制块配对，并结合人工阅读；**未运行 Mermaid 解析器或渲染器**。文档结构检查不是应用测试、云端质量测试或性能验证。

**最终自检**：结果文件落盘后，使用 Node 提取第 4.2 节同一断言脚本并在 Node 子进程中执行，实际输出为 **5 份文档、12 个本地链接及全部断言通过**；另行核验下表 4 个文件指纹与实际内容一致。结果文件也已完整回读，没有将未执行的运行/渲染检查标为通过。

### 4.1 已验证文件指纹

| 文件 | SHA-256 |
| --- | --- |
| `PRD.md` | `5f9849a149696724d7dc9ce0420ba14fc2341c8803e38b1ec74fa92a4798fb91` |
| `README.md` | `63d1fc193ad02ad7fa3f1f28d0f0193a07bbe8ee36034c756c3e8d8bfa4c5822` |
| `docs/architecture.md` | `8b8fa66669c44062ecbc424da968aa779f83a3dd8caeb9f72b47b031e77b6b1b` |
| 本任务 `plan.md` | `64b5a0324f039de223dd2227ca5079a8cd2f9d8f52069954e21ac286b155840b` |

### 4.2 实际执行的可复核断言

下列命令在仓库根执行，脚本仅依赖本机 Node.js 标准库和 Git。原 PRD 使用已有 blob `9570a79f369c359448f28617d9a4b0ddeef15cbc`，先校验其 SHA-256 与实施前基线一致，再比较保留段落。若本结果文件已经存在，脚本也会检查它；预期 Git 状态仅适用于本次工作区快照，后续合法变更后不能沿用旧期望值。

```bash
node <<'NODE'
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { execFileSync: exec } = require('node:child_process');
const task = 'docs/plans/2026-09-12-monorepo-architecture-selection/';
const formal = ['PRD.md', 'README.md', 'docs/architecture.md'];
const result = fs.existsSync(task + 'result.md') ? [task + 'result.md'] : [];
const files = [...formal, task + 'plan.md', ...result];
const read = file => fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
const hash = value => createHash('sha256').update(value).digest('hex');
let links = 0;
for (const file of files) {
  const text = read(file);
  assert.ok(text.endsWith('\n') && !text.includes('\uFFFD'), file);
  let fenced = false, columns = null;
  for (const line of text.split('\n')) {
    assert.ok(!/[ \t]+$/.test(line), file + ': whitespace');
    if (/^```/.test(line)) { fenced = !fenced; columns = null; continue; }
    if (fenced) continue;
    if (line.startsWith('|')) {
      const count = line.replace(/\\\|/g, '').split('|').length - 2;
      if (columns === null) columns = count;
      assert.equal(count, columns, file + ': table');
    } else columns = null;
    for (const [, url] of line.matchAll(/\[[^\]]+\]\(([^\s)]+)\)/g)) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith('#')) continue;
      assert.ok(fs.existsSync(path.resolve(path.dirname(file), decodeURIComponent(url.split('#')[0]))), url);
      links++;
    }
  }
  assert.equal(fenced, false, file + ': fence');
}
for (const file of formal) {
  const text = read(file);
  for (const item of ['frontend/', 'backend/', 'Element Plus', 'PostgreSQL', 'pgvector', 'Celery', 'LangGraph', 'CPU', '云端', 'LLM', 'VLM', 'Embedding', 'NOT_EVALUATED', 'BAAI/bge-m3']) assert.ok(text.includes(item), file + ': ' + item);
  for (const item of ['FastAPI 0.141', 'LangGraph 1.2', 'Vite 8', 'ECharts 6', 'Claude 3.7', '/api/v1/insight/task', 'docs/技术方案.md', 'docs/api.md', 'uv run uvicorn', 'bun run dev', '基于 pgvector 进行相似度聚类']) assert.ok(!text.includes(item), file + ': obsolete ' + item);
}
const prd = read('PRD.md'), arch = read('docs/architecture.md'), plan = read(task + 'plan.md');
const old = exec('git', ['show', '9570a79f369c359448f28617d9a4b0ddeef15cbc'], { encoding: 'utf8' }).replace(/\r\n/g, '\n');
assert.equal(hash(old), '6c902d1548bee452d3e8888c698869063a8cbf24e8a18051e4c7e83786fa0d11');
const part = (text, start, end) => {
  const a = text.indexOf(start), b = text.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, start);
  return text.slice(a, b);
};
for (const [start, end] of [['## 一、', '### 1.3'], ['## 二、', '## 三、'], ['[P1-03]', '[P2-01]'], ['[P2-02]', '## 四、']]) assert.equal(part(prd, start, end), part(old, start, end));
const ids = text => [...text.matchAll(/^\[(P[012]-\d{2})\]/gm)].map(match => match[1]);
assert.deepEqual(ids(prd), ids(old));
for (const value of ['V1.2', '200ms', '30–60', '50ms', '300ms', '99.5%']) assert.ok(prd.includes(value), value);
const diagrams = [...prd.matchAll(/^```mermaid\n([\s\S]*?)^```/gm)];
assert.equal(diagrams.length, 1);
const stack = [];
for (const line of diagrams[0][1].split('\n').map(line => line.trim())) {
  const start = line.match(/^(alt|opt|loop|rect|par|critical|break)\b/);
  if (start) stack.push(start[1]);
  else if (line === 'end') assert.ok(stack.pop());
  else if (/^else\b/.test(line)) assert.equal(stack.at(-1), 'alt');
  else if (/^and\b/.test(line)) assert.equal(stack.at(-1), 'par');
}
assert.equal(stack.length, 0);
assert.ok(plan.includes('- 状态：**已批准**（R1') && plan.includes('R1 批准原文：**“确定”**'));
assert.equal([...arch.matchAll(/^\| S\d+ \|/gm)].length, 24);
const urls = text => new Set([...text.matchAll(/\]\((https?:\/\/[^\s)]+)\)/g)].map(match => match[1]));
assert.ok([...urls(arch)].every(url => urls(plan).has(url)));
const preserved = {
  'AGENTS.md': 'ec98dda0421d90474abb2d193f0d89b2743cf593077da24dc550565e3f35ddc6',
  '.gitignore': '9b46e0734d12f413cb5195415c2760b0739ff7b20378e8aa0338db52da129775',
  'LICENSE': 'ba68068c4082b843f011b0de8a141be606ac7d3957fe24d49ad53c55ead3aa7b',
  'docs/plans/2026-09-12-agents-plan-result-workflow/plan.md': 'dc23c52ed14933f0f7252b4adb5018af000c675d03cf6e79b1504da6dc907fcf',
  'docs/plans/2026-09-12-agents-plan-result-workflow/result.md': '90e08449a0bed41e4929a05d2e268ef4fa4f972b5500671468b99958990ee141'
};
for (const [file, value] of Object.entries(preserved)) assert.equal(hash(fs.readFileSync(file)), value, file);
const status = exec('git', ['status', '--porcelain=v1', '-z', '--untracked-files=all'], { encoding: 'utf8' }).split('\0').filter(Boolean);
assert.deepEqual(status.filter(line => line.startsWith(' M ')), [' M AGENTS.md', ' M README.md']);
const deleted = status.filter(line => line.startsWith(' D '));
assert.equal(deleted.length, 127);
assert.ok(deleted.every(line => !fs.existsSync(line.slice(3))));
const expected = ['PRD.md', 'docs/architecture.md', ...Object.keys(preserved).filter(file => file.startsWith('docs/')), task + 'plan.md', ...result];
assert.deepEqual(status.filter(line => line.startsWith('?? ')).map(line => line.slice(3)).sort(), expected.sort());
assert.equal(status.length, 134 + result.length);
exec('git', ['diff', '--cached', '--exit-code', '--quiet']);
for (const file of ['frontend', 'backend', 'contracts', 'compose.yaml', '.github']) assert.ok(!fs.existsSync(file), file);
console.log(`PASS: ${files.length} documents; ${links} local links; text/tables/fences; cloud/stack/phases; PRD baseline/10 feature IDs/targets; Mermaid block balance; approval/24 source groups; 5 protected hashes; 127 deletions; exact unstaged-only scope.`);
console.log('NOTE: Mermaid renderer, application tests, cloud API calls and performance tests were not run.');
NODE
```

## 5. 计划偏差

- 无实质范围、架构或验收偏差，不需要再次批准。
- 在获批范围内调整表达：原全局 Python 状态示例改为概念状态表，避免把缺失类型写成现有代码；MVP 方框表改为阶段/交付/验收表，统一 P0 与后续能力；SSE 图显式表达并行实时回放。
- PRD 保留原数值目标并补齐测量条件，没有宣称已达标，也没有在实施中降低目标。实际模型 ID、供应商账户与组合版本仍交由后续验证锁定。

## 6. 遗留问题与未执行检查

本轮文档修订没有未解决的实施阻断；下列属于已披露的证据限制和后续验证门禁，不是本任务已经完成的运行能力：

- **官方页面正文**：只获得官方检索摘要/片段；正文直连受 fake-IP/TUN 的 SSRF 安全检查阻止，独立 `source_check` 曾返回 `missing-evidence`。没有绕过安全检查，未把失败核验当通过；架构保留限制说明，外链也未宣称全部在线可达。
- **模型与数据**：未验证 Claude/SiliconFlow 真实账户、区域、准确 model_id、维度/批量顺序、输入限制、质量、限流/额度错误、计费或数据保留条款；未真实采集 Amazon 数据。
- **代码与基础设施**：未安装依赖，未运行前端 build/typecheck/组件/E2E、后端 pytest/lint/typecheck、真实 PostgreSQL/pgvector/Redis 集成、迁移、恢复、租户与云端故障测试。
- **渲染与性能**：未运行 Markdown/Mermaid 渲染器、浏览器视觉验收、压测或 SLA 测量；Node 文档断言不能替代这些验证。
- **后续顺序**：先单独计划并批准 M0 数据与云端模型验证（包括预算/数据授权），再按已确认架构初始化项目和一个真实 ASIN 文本闭环。当前审批不授权执行这些后续工作。
