"""迁移与模型约束测试（无需数据库；真实库验证见阶段 01 计划）。

离线 SQL 等价性已在迁移冻结时用 `alembic upgrade base:head --sql` 新旧渲染
diff 核对：仅新增 9 个唯一约束与 3 个索引，无表/列/类型变化。
"""

import importlib.util
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.db.base import Base

EXPECTED_UNIQUE = {
    "products": ["uq_products_tenant_platform_marketplace_asin"],
    "tasks": ["uq_tasks_tenant_idempotency_key"],
    "task_items": ["uq_task_items_task_product"],
    "reviews": ["uq_reviews_product_source_hash"],
    "snapshot_reviews": ["uq_snapshot_reviews_snapshot_review"],
    "reports": ["uq_reports_item_version"],
    "cluster_members": ["uq_cluster_members_cluster_fragment"],
    "proposal_issues": ["uq_proposal_issues_proposal_cluster"],
    "task_events": ["uq_task_events_task_seq"],
}

EXPECTED_INDEXES = {
    "tasks": ["ix_tasks_tenant_project_created_id"],
    "task_items": ["ix_task_items_task_id"],
    "reviews": ["ix_reviews_product_reviewed_id"],
}

MIGRATION_FILE = Path(__file__).parent.parent / "alembic" / "versions" / "0001_p0_core.py"


def test_table_count():
    assert len(Base.metadata.tables) == 19  # 0001 十八表 + 0003 item_nodes


def test_unique_constraints():
    for table_name, names in EXPECTED_UNIQUE.items():
        table = Base.metadata.tables[table_name]
        found = {
            constraint.name
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        assert set(names) <= found, table_name


def test_indexes():
    for table_name, names in EXPECTED_INDEXES.items():
        table = Base.metadata.tables[table_name]
        assert set(names) <= {index.name for index in table.indexes}, table_name


def _referenced_tables(table):
    return {fk.column.table.name for fk in table.foreign_keys}


def test_every_table_reaches_tenants():
    """连接表经父级外键链路归属租户；本测试验证链路可达，应用层校验见阶段 03/08。"""
    tables = Base.metadata.tables

    def reaches(name, seen):
        if name == "tenants":
            return True
        if name in seen:
            return False
        return any(reaches(ref, seen | {name}) for ref in _referenced_tables(tables[name]))

    for name in tables:
        assert reaches(name, set()), name


def test_migration_module_imports():
    spec = importlib.util.spec_from_file_location("migration_0001", MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0001_p0_core"
    assert module.down_revision is None
    assert callable(module.upgrade)
    assert callable(module.downgrade)
