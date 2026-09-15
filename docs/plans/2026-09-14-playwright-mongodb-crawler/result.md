# Playwright + MongoDB DOM 爬虫：实施结果

## 完成状态

已完成（本任务范围内）。已实现单 URL Playwright + Chromium DOM 抓取、JSON 文件持久化和 MongoDB 同步，并通过离线测试、限定范围静态检查及真实 Chromium + 临时 MongoDB 端到端验证。

## 实际变更

- `backend/pyproject.toml`、`backend/uv.lock`：加入 Playwright 与 PyMongo 依赖并锁定版本。
- `backend/src/insightx/crawler/config.py`：新增爬虫运行时配置，支持 MongoDB、输出目录、超时和无头模式环境变量。
- `backend/src/insightx/crawler/dom.py`：新增固定 DOM 节点契约、跳过规则、递归序列化脚本、规范化 SHA-256、JSON envelope 和临时文件原子替换。
- `backend/src/insightx/crawler/fetch.py`：新增 Playwright Chromium 单页访问与渲染后 DOM 抓取，并保证浏览器资源清理。
- `backend/src/insightx/crawler/storage.py`：新增 `AsyncMongoClient` 存储、`dom_snapshots` 文档写入、三个非唯一索引和幂等关闭。
- `backend/src/insightx/crawler/service.py`：按“抓取成功 -> JSON 写入成功 -> MongoDB 写入成功”的顺序编排单次采集。
- `backend/src/insightx/crawler/__main__.py`、`__init__.py`：新增 `python -m insightx.crawler` CLI 与公开导出。
- `backend/tests/test_crawler_*.py`、`backend/tests/fixtures/crawler/sample.html`：新增 DOM、抓取、存储、编排、CLI 契约测试及本地端到端 fixture。
- `.env.example`、`.gitignore`：补充 MongoDB/爬虫变量模板并忽略爬虫输出。
- `backend/README.md`、`README.md`、`PRD.md`、`docs/architecture.md`：同步 MongoDB 仅保存原始 DOM 快照、PostgreSQL 继续作为业务事实源的边界、CLI 用法和当前实现状态。
- `docs/plans/2026-09-14-playwright-mongodb-crawler/plan.md`：保留已批准计划和真实审批记录。
- `docs/plans/2026-09-14-playwright-mongodb-crawler/result.md`：本结果记录。

## 实施记录

1. 完成 Playwright + Chromium 单 URL 抓取，访问过程使用 `wait_until="domcontentloaded"`，记录最终 URL、标题、HTTP 状态和 UTC 采集时间。
2. 完成 DOM 递归序列化：只输出 element/text 节点，元素标签小写、属性转字符串，跳过 `script`、`style`、`noscript`、`template` 和纯空白文本。
3. 完成 JSON 持久化：使用同一 UUID 命名文件，按规范化 DOM JSON 计算 `dom_sha256`，通过同目录临时文件和 `os.replace` 原子写入。
4. 完成 MongoDB 同步：文档 `_id` 与 `snapshot_id` 相同，写入 DOM、哈希、文件路径、采集元数据和可选租户/任务字段；创建 `source_url + captured_at(desc)`、`dom_sha256`、`tenant_id + task_id + task_item_id + captured_at(desc)` 三个非唯一索引。
5. 完成 CLI 与错误路径：抓取、JSON 写入、MongoDB 写入或成功后的清理失败均返回非零状态；抓取失败后的清理失败不会覆盖原始抓取异常。
6. 完成测试和文档同步，并执行真实本地 HTTP fixture + Chromium + 临时 `mongo:8.0` 容器端到端核验。
7. 相关代码和加固曾分别进入现有提交 `4cce153`、`68f500c`，文档同步进入 `6f825c1`；本任务未主动执行 commit、push、PR 或部署。

## 验证命令与真实结果

在 `backend/` 执行：

- `uv lock --check`：退出码 0，`Resolved 118 packages in 21ms`。
- `uv sync --frozen`：退出码 0，`Checked 116 packages in 15ms`。
- `uv run pytest -q`：退出码 0，`42 passed in 0.15s`。
- `uv run ruff check src/insightx/crawler tests/test_crawler_*.py`：退出码 0，`All checks passed!`。
- `uv run mypy src`：退出码 0，`Success: no issues found in 16 source files`。
- `uv run playwright install chromium`：退出码 0，Chromium 已安装，无额外输出。
- `uv run ruff check .`：退出码 1。仅报告并行后端 API 任务引入的非本任务文件 `src/insightx/models.py:26` 的 `UP017` 和 `src/insightx/models.py:148` 的 `E501`；爬虫文件限定范围检查通过。

真实端到端使用 `tests/fixtures/crawler/sample.html`、Playwright 1.62.0 Chromium 和临时 `mongo:8.0`：

```json
{"snapshot_id":"814096f7c12a48388939c514654102ff","dom_sha256":"34e4bda1335ba22d1aef8337652304c0c95bfd20e5fa598db73e12587f766b4d","final_url":"http://127.0.0.1:8766/sample.html","http_status":200,"mongo_document":true,"indexes":["_id_","dom_sha256","source_url_captured_at","tenant_task_captured_at"],"dom_tags":["body","h1","head","html","main","meta","p","strong","title"]}
```

核验 JSON 与 MongoDB 文档中的 `dom`、`dom_sha256`、`json_path` 一致，状态码为 200，DOM 中不存在 `script`，三个要求的索引均存在。临时 HTTP 服务、MongoDB 容器和临时输出目录已清理，隔离端口已释放。

## 计划偏差

- 全仓 `uv run ruff check .` 未通过，但错误全部来自并行后端 API 任务的 `src/insightx/models.py`，不在本任务获批写入范围；爬虫目录及爬虫测试使用限定范围 Ruff 检查并通过。未修改或掩盖无关错误。
- 本任务加固文件被并行后端 API 提交 `68f500c` 一并提交，最终工作树中功能完整；未发生功能性范围扩展，也未请求额外审批。
- 其余实现与已批准计划一致。

## 遗留问题与未执行检查

- 非 2xx 页面策略未实现：当前记录真实 `http_status`，不因 4xx/5xx 自动失败；该行为属于计划明确的非目标。
- 跨 PostgreSQL/MongoDB 重试幂等、孤儿记录对账、BSON 特殊键和 16 MiB 文档边界未实现，属于本次非目标。
- 未验证生产网站登录、验证码、代理、限流和反爬场景，也未声明绕过这些机制的采集能力。
- 历史提交 `4cce153`、`68f500c` 中误包含 `__pycache__/*.pyc`。本次未清理工作树或改写历史；后续应另行通过仓库清理任务移除并确保忽略规则生效。
- 未执行 commit、push、PR、部署或生产数据变更。
