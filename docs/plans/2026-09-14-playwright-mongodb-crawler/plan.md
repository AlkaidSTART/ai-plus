# Playwright + MongoDB DOM 爬虫：实施计划

## 目标

在 `backend/` 内交付一个可独立运行的最小爬虫闭环：输入单个 `http/https` URL，使用 Playwright + Chromium 访问页面，将渲染后的 DOM 递归序列化为确定性 JSON，原子写入本地 JSON 文件，同时把同一份 DOM 快照及采集元数据写入 MongoDB。提供 CLI、离线单测和真实本地页面/临时 MongoDB 的端到端验收，并同步 PRD、架构与后端运行文档。

本任务只实现“采集并保存原始 DOM 快照”，不进入任务队列、LangGraph、鉴权 API 或评论抽取流程。

## 当前事实及依据

- `backend/pyproject.toml` 当前已有 FastAPI、Pydantic Settings、pytest、Ruff、mypy 等依赖；没有任何 Playwright、PyMongo 或 Motor 依赖。
- `backend/src/insightx/` 当前只有 FastAPI 工厂、路由和硬编码 `degraded` 健康检查，没有配置层、数据库会话、Worker 或采集模块。
- `backend/.venv` 已存在；`uv` 版本为 `0.11.28`。`backend/uv.lock` 当前不包含 Playwright/PyMongo。
- `backend/README.md` 明确数据库连接、Celery Worker、LangGraph 图尚未接入；测试目前完全离线。
- `.env.example` 当前为空；`.gitignore` 当前未忽略爬虫输出目录。
- `docs/architecture.md:101-114`、`docs/architecture.md:158`、`PRD.md:61` 当前把 PostgreSQL/pgvector 描述为原始评论、证据、任务、报告和事件的事实源，并明确 P0 文本快照存 PostgreSQL。
- 用户本次明确要求使用 Playwright 抓取 DOM、解析为 JSON 文件并使用 MongoDB，因此需要调整上述文档中的存储边界，但不能无授权地把 PostgreSQL 从业务事实源中移除。
- PyPI 当前最新版本：`playwright==1.62.0`（Python >= 3.10）、`pymongo==4.18.1`（Python >= 3.9）；本次采用 `playwright>=1.62.0,<2`、`pymongo>=4.18.1,<5`，由 `uv lock` 记录实际解析版本。
- PyMongo 4.18 提供 `AsyncMongoClient`，本次优先使用它，避免引入已进入维护状态的 Motor。
- 本机存在 Docker；是否可启动容器在实施验证时实际检查，不预先宣称可用。

## 存储与数据契约

### 边界决策

- PostgreSQL 继续作为 task、report、evidence、event 和向量的业务事实源。
- MongoDB 只保存爬虫原始 DOM JSON 快照与采集元数据，作为可回查的原始采集产物，不替代 PostgreSQL 业务表。
- 本次不建立跨 PostgreSQL/MongoDB 分布式事务；MongoDB 写入采用不可变快照和同一快照 ID，后续业务引用通过 `snapshot_id`、`content_hash` 对账。

### JSON 文件与 MongoDB 文档

每个成功采集生成一个 UUID `snapshot_id`。JSON 文件使用同一 ID 命名，JSON 文件结构固定为：

```json
{
  "format_version": "1",
  "snapshot_id": "uuid4-hex",
  "source_url": "https://example.com/page",
  "final_url": "https://example.com/page",
  "title": "Page title",
  "captured_at": "2026-09-14T12:00:00.000000Z",
  "http_status": 200,
  "dom_sha256": "64-char-lowercase-hex",
  "dom": {
    "type": "element",
    "tag": "html",
    "attributes": {},
    "children": []
  }
}
```

DOM 节点只使用两种稳定形态：

- 元素节点：`{"type":"element","tag":"...","attributes":{"name":"value"},"children":[...]}`。
- 文本节点：`{"type":"text","text":"..."}`。

序列化规则固定为：

- 从 `document.documentElement` 开始递归遍历。
- 元素标签名转小写；属性全部保留并转换为字符串。
- 文本节点保留文本内容；仅移除纯空白文本节点，不做其他改写。
- 不序列化注释；跳过 `script`、`style`、`noscript`、`template` 元素及其子树，避免把脚本和非展示模板写入快照。
- SVG 元素按普通元素序列化，因此仍保留 `svg`/`path` 等层级；跨域 iframe 只能保留 iframe 元素节点，无法读取其内部文档。
- `dom_sha256` 只对 `dom` 值做规范化 JSON（键排序、无多余空格、UTF-8）后计算，便于同一 DOM 稳定去重/对账。
- JSON 文件先写同目录临时文件，再 `os.replace` 原子替换；内容使用 UTF-8、`ensure_ascii=False`、两空格缩进。

MongoDB 集合默认名为 `dom_snapshots`，文档字段为：

```json
{
  "_id": "与 snapshot_id 相同的 uuid4 字符串",
  "source_url": "https://example.com/page",
  "final_url": "https://example.com/page",
  "title": "Page title",
  "captured_at": "BSON datetime（UTC）",
  "http_status": 200,
  "dom_format_version": "1",
  "dom_sha256": "64-char-lowercase-hex",
  "dom": {},
  "json_path": "/absolute/path/to/snapshot.json",
  "crawler": {"engine": "playwright", "browser": "chromium"},
  "tenant_id": "可选",
  "task_id": "可选",
  "task_item_id": "可选"
}
```

创建以下非唯一索引：`source_url + captured_at(desc)`、`dom_sha256`、`tenant_id + task_id + task_item_id + captured_at(desc)`。同一 DOM 可能被不同时间、任务或租户重复采集，因此不对哈希建立唯一约束。

## 配置

新增 `backend/src/insightx/crawler/config.py`，使用已有 `pydantic-settings` 和项目本地未入库环境文件能力读取配置：

| 变量 | 默认值 | 约束 |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` | 非空连接字符串 |
| `MONGODB_DATABASE` | `insightx` | 非空 |
| `MONGODB_DOM_COLLECTION` | `dom_snapshots` | 非空 |
| `CRAWLER_OUTPUT_DIR` | `artifacts/dom` | CLI 的 `--output-dir` 可覆盖 |
| `CRAWLER_TIMEOUT_MS` | `30000` | 1000–300000 |
| `CRAWLER_HEADLESS` | `true` | CLI 的 `--headed` 可覆盖为 false |

`.env.example` 写入上述变量及安全占位值，不写真实凭证。URL 只从 CLI 或未来受控调用参数传入，禁止在源码中硬编码目标站点。

## 预计变更文件

- `docs/plans/2026-09-14-playwright-mongodb-crawler/plan.md`：本计划。
- `backend/pyproject.toml`：加入 `playwright>=1.62.0,<2`、`pymongo>=4.18.1,<5`。
- `backend/uv.lock`：由 `uv lock` 更新并锁定实际版本。
- `backend/src/insightx/crawler/__init__.py`：导出采集、序列化、存储和编排入口。
- `backend/src/insightx/crawler/config.py`：`CrawlerSettings`、环境变量读取和 CLI 覆盖后的配置校验。
- `backend/src/insightx/crawler/dom.py`：浏览器端 DOM 序列化脚本、DOM 哈希、快照 envelope 构造和原子 JSON 写入。
- `backend/src/insightx/crawler/fetch.py`：Playwright Chromium 启动、页面访问、状态/title/final URL/DOM 获取与资源关闭。
- `backend/src/insightx/crawler/storage.py`：`AsyncMongoClient` 生命周期、集合获取、索引创建和快照写入。
- `backend/src/insightx/crawler/service.py`：抓取 → JSON 文件 → MongoDB 的编排，返回 `CrawlResult`。
- `backend/src/insightx/crawler/__main__.py`：`python -m insightx.crawler` CLI，单 URL、输出目录、headed、可选关联 ID。
- `backend/tests/test_crawler_dom.py`：DOM envelope、哈希稳定性、错误节点和 JSON 原子写入的离线测试。
- `backend/tests/test_crawler_fetch.py`：fake Playwright/browser/page 的在线程测试，不访问真实站点。
- `backend/tests/test_crawler_storage.py`：fake async collection 的 MongoDB 文档与索引契约测试，不连接真实 MongoDB。
- `backend/tests/test_crawler_service.py`：fake fetch/store 验证调用顺序、失败传播和返回结果。
- `backend/tests/test_crawler_cli.py`：参数解析、URL 协议拒绝和 headed 覆盖的离线测试。
- `backend/tests/fixtures/crawler/sample.html`：本地端到端浏览器验收页面。
- `backend/README.md`：补充 MongoDB、Chromium 安装、环境变量、CLI、文件/MongoDB 双写位置和测试说明。
- `docs/architecture.md`：在存储选型、目录边界、运行拓扑和数据边界中补充 MongoDB 原始 DOM 快照职责，并保持 PostgreSQL 业务事实源表述。
- `PRD.md`：在 P0-01 验收标准中区分 MongoDB 原始 DOM/采集元数据与 PostgreSQL 结构化评论/业务数据。
- `README.md`：同步目标架构表中的 MongoDB 原始快照职责，不改产品目标和里程碑。
- `.env.example`：加入上述 MongoDB 和爬虫配置模板。
- `.gitignore`：加入 `backend/artifacts/`，避免提交本地快照。

## 实施步骤与分工

1. 依赖与骨架：主代理按上述版本修改 `backend/pyproject.toml`，执行 `uv lock` 和 `uv sync`；新增 `crawler` 包及各模块的空壳后立即用类型检查确认边界。
2. DOM 契约：实现 `dom.py` 的递归序列化脚本、跳过规则、稳定哈希、JSON envelope 和原子写入；先完成 `test_crawler_dom.py`，再实现到测试通过。
3. 浏览器采集：实现 `fetch.py`，固定使用 `async_playwright()` 的 Chromium、`page.goto(..., wait_until="domcontentloaded", timeout=...)`、`page.evaluate(serializer)`、`page.title()`、`page.url`；用 `try/finally` 关闭 browser/context，并让异常原样向调用方传播。
4. MongoDB 存储：实现 `storage.py`，使用 `AsyncMongoClient`，在进程内建立依赖注入友好的 store；`insert_one` 失败不得吞错；索引创建和客户端关闭需幂等。
5. 编排与 CLI：实现 `service.py` 和 `__main__.py`。CLI 必填 `--url`，只接受 `http/https`；执行顺序必须是抓取成功 → JSON 文件写入成功 → MongoDB 写入成功，任一步失败都返回非零状态并输出明确错误。
6. 文件与文档同步：更新 `.env.example`、`.gitignore`、`backend/README.md`、`README.md`、`docs/architecture.md`、`PRD.md`，只改与本次 MongoDB 原始 DOM 快照边界直接相关的内容。
7. 验证：运行离线质量检查；再以本地 `http.server` 提供静态 HTML，安装 Chromium 后跑真实浏览器采集；若 Docker daemon 可用，启动临时 `mongo:8.0` 容器完成真实 MongoDB 双写并查询一条文档，验证后停止/删除容器。
8. 独立复核：主代理完成实现后，调用一个只读 reviewer 子代理检查代码是否严格符合本计划、测试是否真正覆盖离线契约及文档是否一致；主代理重新执行关键验证并处理批准范围内的问题。
9. 结果记录：全部完成或出现阻塞后，单独创建 `result.md`，逐项记录实际变更、命令、输出、失败和未执行检查，不把结果写入本计划。

分工：主代理负责所有写入、集成和最终验证；已有两个只读探索子代理提供 Playwright/PyMongo 和模块边界结论；实现阶段不拆并行写任务，避免同一小型包内的文件冲突；验证阶段使用一个不参与实现的 reviewer 子代理做独立复核。

## 验证与验收

实施完成后至少执行并记录以下检查：

```bash
cd backend
uv lock --check
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run playwright install chromium
```

端到端验收：

1. 在 `backend/tests/fixtures/crawler/` 放置一个最小静态 HTML（标题、嵌套元素、文本、属性和 `script` 节点），用 `python -m http.server 8765 --directory backend/tests/fixtures/crawler` 提供本地页面。
2. 运行 `MONGODB_URI=mongodb://127.0.0.1:27018 uv run python -m insightx.crawler --url http://127.0.0.1:8765/sample.html`。
3. 断言 stdout 返回 `snapshot_id`、JSON 绝对路径和非空 `dom_sha256`。
4. 读取 JSON 文件，确认标题、最终 URL、状态码、嵌套 DOM 和跳过脚本的规则符合契约。
5. 使用临时 MongoDB 或可用的本地 MongoDB 执行 `find_one({"_id": snapshot_id})`，确认 `dom`、`json_path`、`dom_sha256` 与文件一致，且三个索引存在。
6. 若 Docker 或 MongoDB 不可用，明确记录 MongoDB 端到端检查未执行；不得用 fake 测试冒充真实 MongoDB 验证。

验收条件：离线测试、Ruff、mypy 全部通过；真实 Chromium 能从本地 fixture 抓到预期 DOM 并生成合法 JSON；真实 MongoDB 可用时必须能查到对应文档；文档中的命令、变量名、集合名和代码实际一致。

## 风险与非目标

风险与限制：

- DOM 序列化跳过 script/style/noscript/template，且不读取跨域 iframe；这是可回查的结构快照，不是浏览器内部状态的逐字节镜像。
- 页面可能在 `domcontentloaded` 后继续异步渲染；本次不加入固定 sleep、无限等待或站点专用等待逻辑。
- 单 URL CLI 不处理 Amazon 登录、验证码、代理、旋转指纹、限流或反爬；真实站点抓取能力必须另行验证并遵守授权/robots/服务条款。
- MongoDB 与 PostgreSQL 不做分布式事务；本任务只保证单次快照写入的幂等 ID 和可追踪哈希，不宣称业务链路 exactly-once。
- Playwright Chromium 下载体积较大；CI 缓存和平台差异需要在后续流水线任务中处理。

非目标：

- 不实现批量 URL、评论清洗、ASIN 校验、分页、BSR/价格抽取或评论字段结构化。
- 不接入 Celery、LangGraph、SSE、FastAPI 路由、认证/租户 API 或 outbox。
- 不替换 PostgreSQL 业务事实源，不建立 PostgreSQL 中的 `mongo_artifact_id` 字段或迁移；该关联留给后续任务。
- 不部署生产 MongoDB、不新增 `compose.yaml`、不修改云端模型或前端。
- 不执行 git commit、push、PR、发布或生产环境操作。

## 审核状态

- 状态：已批准
- 创建日期：2026-09-14
- 批准信息：2026-09-14；用户原文：“开始”
