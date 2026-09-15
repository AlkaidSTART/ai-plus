# Amazon 商品数据库自动接入计划

## 目标

把任务创建从“手工输入 ASIN”改为“选择品类或关键词种子”，由异步采集链路自动生成 ASIN 池，再进入商品详情、竞品关系和持久化流程。

## 范围

1. 新增 `insightx.catalog` 领域包，负责 Amazon 搜索页、类目页和关联商品页到 ASIN 候选的解析、去重、来源追踪和持久化。
2. 新增 catalog ORM 与 Alembic 迁移；PostgreSQL 保存商品事实、候选、关系、采集批次和调度定义，MongoDB 仅保留原始 DOM。
3. 扩展任务创建契约：`source` 支持 `CATEGORY` 与 `KEYWORDS`，保留旧 `asins` 兼容，但前端不再暴露手工 ASIN 输入。
4. 空 ASIN 池必须在持久化任务前以 `409 ASIN_POOL_EMPTY` 失败；Playwright 发现不得在同步 HTTP 路径运行。
5. 新增品类/关键词种子 API，并从持久化 ASIN 池生成 `TaskItem`。
6. 新增 Celery Beat 调度：08:00 关键词搜索、10:00 类目扫描、12:00 新 ASIN 扫描、14:00 价格、16:00 评论数、18:00 排名；时区固定 `Asia/Shanghai`。
7. 更新 Docker Compose、环境变量、前端类型/客户端/对话框与文档。
8. 用 fake fetcher 做离线测试，不访问真实 Amazon。

## 架构

```text
Category / Keyword Seed
        |
  Amazon Discovery (Worker/Beat only)
        |
 Search + Category pages -> ASIN candidates
        |
 Related Products -> competitor ASIN candidates
        |
 dedupe + provenance -> persisted ASIN pool
        |
 TaskItem / Product detail / snapshots
```

## 风险与约束

- 不修改当前工作区已有的 `backend/src/insightx/services/worker.py` 未提交改动。
- Amazon 页面结构和条款会变化；解析器必须保留链接正则回退，并受限流、重试和审计约束。
- 未真实接入 Amazon 页面或验证生产代理前，不宣称生产可用。
- `source` 与旧 `asins` 至少一个，且不能同时提供；`source` 必须进入幂等请求哈希。
- 调度任务只负责编排和持久化，不把浏览器抓取放进同步 API。

## 实施顺序

1. Catalog 模型、配置、schema、迁移。
2. 解析器与 discovery/storage/service，配合离线测试。
3. 改造任务来源解析、候选池持久化和旧接口兼容。
4. 增加 catalog API 与 router 注册。
5. 增加 Celery app、Beat 和六类作业。
6. 增加 compose beat/MongoDB 配置及环境变量。
7. 改造前端为品类/关键词来源选择并清理手工 ASIN 文案。
8. 运行后端、前端和迁移验证，记录到 result.md。
