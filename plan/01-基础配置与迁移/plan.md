# 阶段 01：基础配置与迁移

## 目标与前置条件

让现有单包双入口骨架具备可复现配置、确定性迁移和可靠的测试入口，不在本阶段实现采集或任务业务。

先读 [总纲](../00-后端实施总纲/plan.md)、`backend/README.md`、`app/config.py`、`db/models.py`、Alembic 配置及 Compose。数据库操作仅限明确批准的隔离测试库；未确认现有迁移是否应用前，不覆盖历史迁移。

## 当前缺口

- Alembic 将 asyncpg URL 转成默认同步驱动，本环境缺少 psycopg2，而项目实际声明 psycopg 3。
- 0001 从可变 ORM metadata 建表/删表，不具备稳定历史重放语义。
- ORM 声明 18 表但没有注释承诺的业务唯一约束和查询索引。
- Compose 未定义 worker 和迁移入口；`BACKEND_CORS_ORIGINS` 与 `cors_origins` 不一致；若干 store/provider 变量无对应代码。
- 示例预置项目/租户 ID 与 UUID 字段不兼容；pytest 的 asyncio_mode 没有对应插件支持。

## 文件范围

已有：`backend/app/config.py`、`backend/app/db/models.py`、`backend/app/db/session.py`、`backend/alembic/env.py`、`backend/alembic/versions/0001_p0_core.py`、`backend/pyproject.toml`、`backend/uv.lock`、`backend/Dockerfile`、`backend/README.md`、`backend/tests/conftest.py`、根 README、`docker-compose.yml`、`docs/api.md`、`docs/技术方案.md`。

拟新增：必要的增量迁移、`backend/tests/test_config.py`、`backend/tests/test_migrations.py`、仅开发使用的最小预置数据入口（具体文件在确认 UUID 与播种方式后确定）。不要新增通用部署平台。

## 实施步骤

- [ ] 核实当前 lock 与实际 Python/数据库版本，复现两项冒烟测试和驱动失败；保留基线。
- [ ] 明确测试数据库、迁移历史及现有数据情况。若 0001 已应用或无法确认，停止改写它，先确认兼容迁移策略；确认从未使用时才可将初始迁移改为显式且固定的 DDL。
- [ ] 使用已声明的 psycopg 3 同步方言，按 SQLAlchemy 当前版本文档进行结构化 URL 转换，保留用户名、密码、端口、查询参数，不靠宽泛字符串替换。
- [ ] 固化初始 18 表结构或使用获批兼容策略；验证 upgrade 可重放、重复 upgrade 无副作用，隔离临时库 downgrade/upgrade 不依赖未来 ORM 变化。不得在未知数据库执行 drop_all。
- [ ] 建立目前可确定的唯一约束：产品租户/平台/站点/ASIN、任务租户/幂等键、分项 task/product、事件 task/seq、簇成员、建议关联及报告版本；评论版本和快照选择约束依照原文版本语义设计。先检查重复数据再迁移，不静默删除冲突记录。
- [ ] 补 P0 必需的任务列表、事件与关联查询索引；向量 HNSW 留给阶段 06，不能仅凭 vector 列存在宣布检索已完成。
- [ ] 对连接表采用可验证的父级租户链路与同报告约束；如需组合外键或新列，仅补满足隔离的最小结构，不把应用约束写成数据库已经保证。
- [ ] 统一 Settings/Compose 环境变量与 CORS 列表解析格式，删除或明确未消费的开发配置；核实 AsyncSession 生成器类型和连接释放。
- [ ] 生成合法、稳定、可重复播种的本地 tenant/project UUID，禁止用 project_home 直接写 UUID；生产禁用开发播种/预置身份。
- [ ] Compose 增加独立 API/worker 启动及明确迁移步骤、就绪检查。当前 worker 空轮询应如实标注；Redis 不能成为任务事实存储或本地闭环硬依赖。
- [ ] 按实际测试需求决定移除无效 asyncio 配置或引入必要插件；核查测试客户端弃用告警兼容性，不见警告就盲目新增 httpx2。
- [ ] 修正根 README 启动入口为 app.main:app，修复现状与文档链接，明确业务端点仍占位。PRD 的版本/业务差异需确认，不擅自升级 PostgreSQL 或改技术路线。

## 验证与验收

```bash
cd backend
uv sync --frozen
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
```

上述数据库命令必须指向隔离测试库。先检查环境和授权，再执行；无 uv 时可用已有虚拟环境运行测试，但不可声称验证了 uv 同步。

- [ ] 隔离库验证 18 表和扩展实际存在，约束违规被拒绝；重复 upgrade 不改变数据。
- [ ] 在可销毁测试库验证回退/重建；已应用旧迁移的兼容路径需单独覆盖。
- [ ] API/worker 从约定入口启动；API `/health` 与数据库就绪含义清晰；配置错误可诊断。
- [ ] CORS 来源生效；Compose 配置可解析，未读取无效变量造成虚假运行模式。
- [ ] 不依赖真实采集/模型密钥即可复现基础测试。记录告警真实处置结果。

## 非目标与停止条件

不实现任务执行、登录平台、真实采集或模型节点；不将 Redis/Celery、MinIO 提前铺入 P0。未知迁移历史、数据库版本决策或生产环境权限未确认时，停在相关操作前。

## 交接

向阶段 03 提供可用测试库、合法预置 UUID、会话工厂、迁移策略和测试命令；向阶段 02 提供实际运行环境与已验证版本，不给未经验证的兼容承诺。
