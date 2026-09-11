"""任务持久化服务（api.md §4、§7）。

纯函数（ASIN 规范化、日期窗、幂等哈希、游标编解码）可离线单测；
DB 函数需要隔离 PostgreSQL（UUID/约束/事务语义，不用 SQLite 代替）。

调用约定：每个公开 DB 函数自己管理事务，调用方须使用 fresh session，
不得在调用前后复用同一 session 做裸 execute（SQLAlchemy autobegin 会
与显式 begin 冲突）。
"""

import base64
import hashlib
import json
import uuid
from calendar import monthrange
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TaskStatus, Window
from app.db.models import ItemNode, Product, Project, Report, Task, TaskEvent, TaskItem
from app.worker.nodes import NODE_ORDER

SITE_TZ = ZoneInfo("America/New_York")
TASK_LIST_DEFAULT_LIMIT = 20
TASK_LIST_MAX_LIMIT = 100
TOTAL_NODES = len(NODE_ORDER)
TERMINAL_STATUSES = (
    TaskStatus.COMPLETED.value,
    TaskStatus.FAILED.value,
    TaskStatus.CANCELED.value,
)


class ProjectNotFound(Exception):
    pass


class TaskNotFound(Exception):
    pass


class NotRetryable(Exception):
    pass


class IdempotencyConflict(Exception):
    def __init__(self, task_id: uuid.UUID) -> None:
        super().__init__("相同幂等键提交了不同内容")
        self.task_id = task_id


class _RaceRetry(Exception):
    """内部并发竞态信号：外层循环重试一次，外界不可见。"""


def site_today() -> date:
    return datetime.now(SITE_TZ).date()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_asins(asins: list[str]) -> list[str]:
    """大写规范化并去重，排序保证同一集合的稳定表示。"""
    return sorted({a.upper() for a in asins})


def minus_calendar_months(end: date, months: int) -> date:
    total = end.year * 12 + (end.month - 1) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    return date(year, month, min(end.day, monthrange(year, month)[1]))


def resolve_window(
    start: date | None, end: date | None, today: date
) -> tuple[date, date]:
    """解析日期窗。缺省为站点当前日向前六个日历月（短月夹至月末）；非法抛 ValueError。"""
    if (start is None) != (end is None):
        raise ValueError("时间窗须同时给出起止日期")
    if start is None or end is None:
        end = today
        return minus_calendar_months(end, 6), end
    if start > end:
        raise ValueError("时间窗开始日期不得晚于结束日期")
    if end > today:
        raise ValueError("时间窗结束日期不得晚于站点当前日")
    return start, end


def canonical_intent(
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    asins: list[str],
    platform: str,
    marketplace: str,
    window_given: Window | None,
) -> dict:
    """幂等哈希只覆盖客户端提交意图（含缺省标记），不含解析后的日期。

    同一缺省请求在不同站点日期重放时哈希稳定，返回原任务及其冻结窗口。
    """
    return {
        "tenant_id": str(tenant_id),
        "project_id": str(project_id),
        "asins": normalize_asins(asins),
        "platform": platform,
        "marketplace": marketplace,
        "window_given": (
            None
            if window_given is None
            else {
                "start_date": window_given.start_date.isoformat(),
                "end_date": window_given.end_date.isoformat(),
            }
        ),
    }


def intent_hash(intent: dict) -> str:
    return hashlib.sha256(
        json.dumps(intent, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _filter_fp(project_id: uuid.UUID | None, status: str | None) -> str:
    return hashlib.sha256(f"{project_id}|{status or ''}".encode()).hexdigest()[:16]


def encode_cursor(
    created_at: datetime, task_id: uuid.UUID, project_id: uuid.UUID | None, status: str | None
) -> str:
    payload = {
        "c": created_at.isoformat(),
        "id": str(task_id),
        "fp": _filter_fp(project_id, status),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def decode_cursor(
    cursor: str, project_id: uuid.UUID | None, status: str | None
) -> tuple[datetime, uuid.UUID]:
    """游标绑定过滤条件；指纹不符或格式非法抛 ValueError（路由转为 422）。"""
    payload: object = None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("fp") != _filter_fp(project_id, status):
            raise ValueError("游标与当前过滤条件不匹配")
        return datetime.fromisoformat(payload["c"]), uuid.UUID(payload["id"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        if not isinstance(payload, dict):
            raise ValueError("非法游标") from exc
        raise ValueError("非法游标") from exc


def _task_links(task_id: uuid.UUID) -> dict:
    base = f"/api/v1/insight/task/{task_id}"
    return {"self": base, "events": f"{base}/events"}


async def _get_project(
    session: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> Project | None:
    result = await session.execute(
        select(Project).where(
            Project.id == project_id, Project.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_product(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    platform: str,
    marketplace: str,
    asin: str,
) -> Product:
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.platform == platform,
        Product.marketplace == marketplace,
        Product.asin == asin,
    )
    product = (await session.execute(stmt)).scalar_one_or_none()
    if product is not None:
        return product
    try:
        async with session.begin_nested():
            product = Product(
                tenant_id=tenant_id,
                platform=platform,
                marketplace=marketplace,
                asin=asin,
            )
            session.add(product)
            await session.flush()
        return product
    except IntegrityError:
        pass
    product = (await session.execute(stmt)).scalar_one_or_none()
    if product is None:
        raise _RaceRetry()
    return product


async def _load_items(
    session: AsyncSession, task_id: uuid.UUID
) -> list[tuple[TaskItem, str]]:
    result = await session.execute(
        select(TaskItem, Product.asin)
        .join(Product, TaskItem.product_id == Product.id)
        .where(TaskItem.task_id == task_id)
        .order_by(Product.asin)
    )
    return [(row[0], row[1]) for row in result.all()]


def _item_counts(items: list[tuple[TaskItem, str]]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "canceled": 0,
    }
    for item, _ in items:
        key = item.status.lower()
        if key in counts:
            counts[key] += 1
    return counts


async def _insert_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    intent: dict,
    digest: str,
    idempotency_key: str,
    resolved_window: tuple[date, date],
    parent_task_id: uuid.UUID | None,
) -> dict:
    products = [
        await _get_or_create_product(
            session, tenant_id, intent["platform"], intent["marketplace"], asin
        )
        for asin in intent["asins"]
    ]
    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        input={
            "asins": intent["asins"],
            "platform": intent["platform"],
            "marketplace": intent["marketplace"],
            "window_given": intent["window_given"],
            "window_resolved": {
                "start_date": resolved_window[0].isoformat(),
                "end_date": resolved_window[1].isoformat(),
            },
        },
        status=TaskStatus.QUEUED.value,
        phase="P0",
        idempotency_key=idempotency_key,
        request_hash=digest,
        parent_task_id=parent_task_id,
    )
    session.add(task)
    await session.flush()
    for product in products:
        session.add(
            TaskItem(
                tenant_id=tenant_id,
                task_id=task.id,
                product_id=product.id,
                status=TaskStatus.QUEUED.value,
            )
        )
    await session.flush()
    items = await _load_items(session, task.id)
    occurred = utcnow()
    session.add(
        TaskEvent(
            tenant_id=tenant_id,
            task_id=task.id,
            seq=1,
            type="task.updated",
            occurred_at=occurred,
            payload={
                "status": task.status,
                "item_counts": _item_counts(items),
                "item_id": None,
                "attempt": None,
                "occurred_at": occurred.isoformat(),
            },
        )
    )
    await session.flush()
    return {
        "task_id": str(task.id),
        "status": task.status,
        "phase": task.phase,
        "reused": False,
        "window": {
            "start_date": resolved_window[0].isoformat(),
            "end_date": resolved_window[1].isoformat(),
        },
        "items": [
            {"item_id": str(item.id), "asin": asin, "status": item.status}
            for item, asin in items
        ],
        "links": _task_links(task.id),
    }


async def create_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    platform: str,
    marketplace: str,
    asins: list[str],
    window_given: Window | None,
    idempotency_key: str,
    parent_task_id: uuid.UUID | None = None,
    today: date | None = None,
) -> dict:
    """创建任务。幂等：同键同内容返回原任务（reused=true），同键不同内容抛 IdempotencyConflict。"""
    intent = canonical_intent(
        tenant_id, project_id, asins, platform, marketplace, window_given
    )
    digest = intent_hash(intent)
    resolved_window = resolve_window(
        window_given.start_date if window_given else None,
        window_given.end_date if window_given else None,
        today or site_today(),
    )
    for _ in range(2):
        try:
            async with session.begin():
                project = await _get_project(session, tenant_id, project_id)
                if project is None:
                    raise ProjectNotFound()
                if project.marketplace != marketplace:
                    raise ProjectNotFound()
                return await _insert_task(
                    session,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    intent=intent,
                    digest=digest,
                    idempotency_key=idempotency_key,
                    resolved_window=resolved_window,
                    parent_task_id=parent_task_id,
                )
        except (IntegrityError, _RaceRetry):
            pass
        async with session.begin():
            result = await session.execute(
                select(Task).where(
                    Task.tenant_id == tenant_id,
                    Task.idempotency_key == idempotency_key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                if existing.request_hash == digest:
                    items = await _load_items(session, existing.id)
                    created = {
                        "task_id": str(existing.id),
                        "status": existing.status,
                        "phase": existing.phase,
                        "reused": True,
                        "window": existing.input["window_resolved"],
                        "items": [
                            {"item_id": str(item.id), "asin": asin, "status": item.status}
                            for item, asin in items
                        ],
                        "links": _task_links(existing.id),
                    }
                    if existing.parent_task_id is not None:
                        created["parent_task_id"] = str(existing.parent_task_id)
                    return created
                raise IdempotencyConflict(existing.id)
    raise RuntimeError("任务创建并发重试耗尽")


def _node_states(rows: list[ItemNode]) -> tuple[list[dict], int]:
    """同一节点取最大 output_version；返回（按 NODE_ORDER 排序的状态，COMPLETED 数）。"""
    by_node: dict[str, ItemNode] = {}
    for row in rows:
        current = by_node.get(row.node)
        if current is None or row.output_version > current.output_version:
            by_node[row.node] = row
    ordered = []
    completed = 0
    for node in NODE_ORDER:
        row = by_node.get(node)
        if row is None:
            continue
        if row.status == TaskStatus.COMPLETED.value:
            completed += 1
        ordered.append(
            {
                "key": row.node,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "output_summary": row.output_summary,
                "skip_reason": row.skip_reason,
            }
        )
    return ordered, completed


async def get_snapshot(
    session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID
) -> dict | None:
    """一致性快照：同一事务内读取任务、分项与 last_event_id。"""
    async with session.begin():
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == tenant_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return None
        items = await _load_items(session, task.id)
        last_seq = await session.execute(
            select(func.max(TaskEvent.seq)).where(TaskEvent.task_id == task.id)
        )
        max_seq = last_seq.scalar() or 0
        report_ids: dict = {}
        if items:
            id_rows = await session.execute(
                select(Report.item_id, Report.id, Report.version).where(
                    Report.item_id.in_([item.id for item, _ in items])
                )
            )
            best: dict = {}
            for item_id, report_id, version in id_rows.all():
                if item_id not in best or version > best[item_id][0]:
                    best[item_id] = (version, report_id)
            report_ids = {item_id: str(report_id) for item_id, (_, report_id) in best.items()}
        warnings = await session.execute(
            select(TaskEvent).where(
                TaskEvent.task_id == task.id, TaskEvent.type == "warning"
            )
        )
        attempts = {str(item.id): item.attempt for item, _ in items}
        grouped: dict[str, list] = {}
        if items:
            node_rows = await session.execute(
                select(ItemNode).where(
                    ItemNode.item_id.in_([item.id for item, _ in items])
                )
            )
            for row in node_rows.scalars().all():
                key = str(row.item_id)
                if key in attempts and row.attempt == attempts[key]:
                    grouped.setdefault(key, []).append(row)
        node_states = {
            key: _node_states(grouped.get(key, [])) for key in attempts
        }
        snapshot = {
            "task_id": str(task.id),
            "project_id": str(task.project_id),
            "phase": task.phase,
            "status": task.status,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "cancel_requested_at": task.cancel_requested_at,
            "last_event_id": str(max_seq),
            "item_counts": _item_counts(items),
            "items": [
                {
                    "item_id": str(item.id),
                    "asin": asin,
                    "status": item.status,
                    "attempt": item.attempt,
                    "current_node": item.current_node,
                    "nodes": node_states[str(item.id)][0],
                    "progress": {
                        "completed_nodes": node_states[str(item.id)][1],
                        "total_nodes": TOTAL_NODES,
                        "processed_reviews": 0,
                        "total_reviews": None,
                    },
                    "report_id": report_ids.get(item.id),
                    "error": item.error,
                }
                for item, asin in items
            ],
            "warnings": [
                {
                    "code": event.payload.get("code", ""),
                    "message": event.payload.get("message", ""),
                    "item_id": str(event.item_id)
                    if event.item_id is not None
                    else None,
                }
                for event in warnings.scalars().all()
            ],
        }
        return snapshot


async def list_tasks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID | None,
    status: str | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict], str | None]:
    """稳定分页：created_at DESC、id DESC；游标绑定过滤条件。"""
    async with session.begin():
        stmt = select(Task).where(Task.tenant_id == tenant_id)
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if cursor is not None:
            cursor_created, cursor_id = decode_cursor(cursor, project_id, status)
            stmt = stmt.where(
                (Task.created_at < cursor_created)
                | ((Task.created_at == cursor_created) & (Task.id < cursor_id))
            )
        stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc()).limit(limit + 1)
        rows = (await session.execute(stmt)).scalars().all()
        overflow = len(rows) > limit
        rows = rows[:limit]
        items = []
        for task in rows:
            task_items = await _load_items(session, task.id)
            warning_count = await session.execute(
                select(func.count())
                .select_from(TaskEvent)
                .where(
                    TaskEvent.task_id == task.id, TaskEvent.type == "warning"
                )
            )
            items.append(
                {
                    "task_id": str(task.id),
                    "project_id": str(task.project_id),
                    "created_at": task.created_at,
                    "status": task.status,
                    "asins": [asin for _, asin in task_items],
                    "item_counts": _item_counts(task_items),
                    "warnings_count": warning_count.scalar() or 0,
                }
            )
        next_cursor = None
        if overflow and rows:
            last = rows[-1]
            next_cursor = encode_cursor(
                last.created_at, last.id, project_id, status
            )
        return items, next_cursor


async def cancel_task(
    session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID
) -> dict | None:
    """记录取消请求（首次为准）。终态任务返回原状态；实际停止由 worker 落实（阶段 04）。"""
    async with session.begin():
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == tenant_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return None
        if task.status in TERMINAL_STATUSES:
            return {
                "task_id": str(task.id),
                "status": task.status,
                "cancel_requested_at": task.cancel_requested_at,
            }
        if task.cancel_requested_at is None:
            task.cancel_requested_at = utcnow()
            await session.flush()
        return {
            "task_id": str(task.id),
            "status": task.status,
            "cancel_requested_at": task.cancel_requested_at,
        }


async def retry_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_task_id: uuid.UUID,
    item_ids: list[str],
    idempotency_key: str,
) -> dict:
    """从已终结源任务的 FAILED 分项建新任务；保留源历史，不复用旧 task ID。"""
    deduped = list(dict.fromkeys(item_ids))
    if not deduped or len(deduped) > 10:
        raise NotRetryable()
    try:
        wanted = [uuid.UUID(item_id) for item_id in deduped]
    except ValueError as exc:
        raise NotRetryable() from exc
    async with session.begin():
        result = await session.execute(
            select(Task).where(
                Task.id == source_task_id, Task.tenant_id == tenant_id
            )
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise TaskNotFound()
        if source.status not in TERMINAL_STATUSES:
            raise NotRetryable()
        items = await _load_items(session, source.id)
        by_id = {item.id: (item, asin) for item, asin in items}
        selected = []
        for wanted_id in wanted:
            entry = by_id.get(wanted_id)
            if entry is None or entry[0].status != TaskStatus.FAILED.value:
                raise NotRetryable()
            selected.append(entry[1])
        resolved = source.input["window_resolved"]
    window = Window(
        start_date=date.fromisoformat(resolved["start_date"]),
        end_date=date.fromisoformat(resolved["end_date"]),
    )
    created = await create_task(
        session,
        tenant_id=tenant_id,
        project_id=source.project_id,
        platform=source.input["platform"],
        marketplace=source.input["marketplace"],
        asins=selected,
        window_given=window,
        idempotency_key=idempotency_key,
        parent_task_id=source.id,
    )
    created["parent_task_id"] = str(source.id)
    return created
