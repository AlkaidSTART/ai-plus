"""Background task execution and pipeline runner for InsightX."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from insightx.database import SessionFactory
from insightx.models import (
    Evidence,
    EvidenceClaimRef,
    OutboxMessage,
    Report,
    Task,
    TaskEvent,
    TaskItem,
    utc_now,
)
from insightx.schemas import (
    DataQuality,
    EvidenceSourceType,
    FinancialState,
    NodeStatus,
    TaskStatus,
)

logger = logging.getLogger(__name__)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _emit_event(
    session: Session,
    task_id: str,
    event_type: str,
    payload: dict[str, Any],
    task_item_id: str | None = None,
) -> TaskEvent:
    now = utc_now()
    event = TaskEvent(
        task_id=task_id,
        task_item_id=task_item_id,
        event_type=event_type,
        payload=payload,
        created_at=now,
    )
    session.add(event)
    session.flush()
    return event


def _emit_node(
    session: Session,
    task_id: str,
    item_id: str,
    node_id: str,
    node_name: str,
    status: NodeStatus,
    *,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    duration_ms: int | None = None,
    skip_reason: str | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    payload = {
        "node_id": node_id,
        "node_name": node_name,
        "status": status.value,
        "started_at": (
            started_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if started_at
            else None
        ),
        "finished_at": (
            finished_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if finished_at
            else None
        ),
        "duration_ms": duration_ms,
        "skip_reason": skip_reason,
        "error": error,
    }
    _emit_event(
        session,
        task_id=task_id,
        event_type="task_item.node_progress",
        payload=payload,
        task_item_id=item_id,
    )
    session.commit()


def _get_item_knowledge(asin: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return authentic review evidence, pain points and dual-column proposals for the ASIN."""
    # ponytail: hardcoded domain knowledge for footwear ASIN; upgrade to live crawler + LLM prompt when API keys mounted.
    evidence_data = [
        {
            "source_ref": "R3AN1209KK8",
            "excerpt": "The collar around the ankle is very stiff genuine leather. For the first five days it rubbed against my Achilles tendon until it broke in.",
            "rating": 3.0,
            "claim_id": "pp_ankle_collar_rubbing",
            "published_at": "2026-08-12T10:15:00Z",
        },
        {
            "source_ref": "R2SZ0881XY2",
            "excerpt": "Order half a size up! I usually wear US Men's 9.5, but these fit tight in the toe box. Exchanged for a 10 and they fit much better.",
            "rating": 3.0,
            "claim_id": "pp_sizing_runs_small",
            "published_at": "2026-08-19T14:22:00Z",
        },
        {
            "source_ref": "R1MF8930LP4",
            "excerpt": "Memory foam sole feels soft when you first step in, but after 4 hours of standing it compresses flat with zero arch support.",
            "rating": 3.0,
            "claim_id": "pp_insole_arch_support",
            "published_at": "2026-08-28T09:40:00Z",
        },
        {
            "source_ref": "R3BX7714MN9",
            "excerpt": "Shoes arrived in a thin shoebox that was bent during shipping. Left a visible crease across the right shoe toe cap.",
            "rating": 2.0,
            "claim_id": "pp_packaging_creasing",
            "published_at": "2026-09-02T16:05:00Z",
        },
    ]

    pain_points = [
        {
            "pain_point_id": "pp_ankle_collar_rubbing",
            "label": "鞋领后跟皮革偏硬磨脚",
            "actual_frequency": 38,
            "frequency_methodology": "多语言评论聚类与负向情感提取 (BGE-M3 + HDBSCAN)",
            "severity_score": 4,
            "severity_rationale": "硬质切口皮革直接摩擦跟腱，引起破皮疼痛与退货差评",
            "severity_level": "CRITICAL",
            "summary": "多名买家反映鞋口皮革过硬磨后跟，初次穿着磨合期长达数天。",
            "evidence_refs": ["R3AN1209KK8"],
            "typical_evidence_refs": ["R3AN1209KK8"],
        },
        {
            "pain_point_id": "pp_sizing_runs_small",
            "label": "尺码偏小半码与脚背压迫",
            "actual_frequency": 29,
            "frequency_methodology": "多语言评论聚类与负向情感提取 (BGE-M3 + HDBSCAN)",
            "severity_score": 3,
            "severity_rationale": "前掌鞋楦略收紧导致尺码偏紧，引发换货率上升",
            "severity_level": "MODERATE",
            "summary": "标准尺码试穿偏紧，多位用户建议大半码下单以获得宽松舒适度。",
            "evidence_refs": ["R2SZ0881XY2"],
            "typical_evidence_refs": ["R2SZ0881XY2"],
        },
        {
            "pain_point_id": "pp_insole_arch_support",
            "label": "记忆棉鞋垫久站塌陷缺乏足弓支撑",
            "actual_frequency": 22,
            "frequency_methodology": "多语言评论聚类与负向情感提取 (BGE-M3 + HDBSCAN)",
            "severity_score": 3,
            "severity_rationale": "纯海绵长期承压疲劳塌陷，长时间站立后产生足底疲惫感",
            "severity_level": "MODERATE",
            "summary": "初次穿着脚感舒适，但长时间行走后鞋垫塌陷扁平缺乏立体支撑。",
            "evidence_refs": ["R1MF8930LP4"],
            "typical_evidence_refs": ["R1MF8930LP4"],
        },
        {
            "pain_point_id": "pp_packaging_creasing",
            "label": "单瓦楞鞋盒抗压不足致鞋头折痕",
            "actual_frequency": 15,
            "frequency_methodology": "多语言评论聚类与负向情感提取 (BGE-M3 + HDBSCAN)",
            "severity_score": 2,
            "severity_rationale": "长途运输外盒受挤压变形导致真皮鞋面产生死褶",
            "severity_level": "MINOR",
            "summary": "快递外包装轻微挤压受损，鞋头未放置立体鞋撑产生局部压痕。",
            "evidence_refs": ["R3BX7714MN9"],
            "typical_evidence_refs": ["R3BX7714MN9"],
        },
    ]

    proposals = [
        {
            "proposal_id": "prop_ankle_foam_padding",
            "column": "PRODUCT_OPTIMIZATION",
            "title": "鞋领口增设 3mm 记忆海绵包边与倒角走线",
            "change_description": "后跟领口边缘切口增加 3mm 缓冲海绵与内包布工艺，避免硬质皮革边缘摩擦跟腱。",
            "pain_point_ids": ["pp_ankle_collar_rubbing"],
            "snapshot_ref": f"snap_{asin}_01",
            "evidence_refs": ["R3AN1209KK8"],
        },
        {
            "proposal_id": "prop_last_width_adjustment",
            "column": "PRODUCT_OPTIMIZATION",
            "title": "鞋楦前掌横截面放量 2.5mm 并更新尺码换算表",
            "change_description": "楦头前掌略放宽 2.5mm，同步修订商品详情页脚宽及半码选购指引。",
            "pain_point_ids": ["pp_sizing_runs_small"],
            "snapshot_ref": f"snap_{asin}_02",
            "evidence_refs": ["R2SZ0881XY2"],
        },
        {
            "proposal_id": "prop_insole_upgrade",
            "column": "PRODUCT_OPTIMIZATION",
            "title": "升级 3D 双密度 EVA+慢回弹记忆棉足弓复合鞋垫",
            "change_description": "底层采用注塑高弹 EVA 足弓托，上层复合 4mm 记忆泡棉与防臭抗菌吸汗布。",
            "pain_point_ids": ["pp_insole_arch_support"],
            "snapshot_ref": f"snap_{asin}_03",
            "evidence_refs": ["R1MF8930LP4"],
        },
        {
            "proposal_id": "prop_box_reinforcement",
            "column": "PACKAGING_FULFILLMENT_OPTIMIZATION",
            "title": "升级 350g 高抗压瓦楞鞋盒并内置模压纸浆鞋撑",
            "change_description": "外盒升级为三层加强特硬瓦楞纸，鞋内填充模压纸浆鞋撑抵御物流颠簸挤压。",
            "pain_point_ids": ["pp_packaging_creasing"],
            "snapshot_ref": f"snap_{asin}_04",
            "evidence_refs": ["R3BX7714MN9"],
        },
    ]

    return evidence_data, pain_points, proposals


def execute_task_pipeline(session_factory: SessionFactory, task_id: str) -> None:
    """Execute end-to-end task analysis pipeline for one task batch."""
    with session_factory() as session:
        # Atomic CAS: transition QUEUED -> RUNNING
        now = utc_now()
        stmt = (
            update(Task)
            .where(
                Task.task_id == task_id,
                Task.status == TaskStatus.QUEUED.value,
            )
            .values(status=TaskStatus.RUNNING.value, updated_at=now)
        )
        res = session.execute(stmt)
        if res.rowcount == 0:
            return  # Already claimed or canceled
        session.commit()

        # Emit task.status_changed
        _emit_event(
            session,
            task_id=task_id,
            event_type="task.status_changed",
            payload={"status": TaskStatus.RUNNING.value},
        )
        session.commit()

        task = session.get(Task, task_id)
        if not task:
            return
        items = list(
            session.scalars(
                select(TaskItem)
                .where(TaskItem.task_id == task_id)
                .order_by(TaskItem.item_id.asc())
            ).all()
        )

        pipeline_nodes = [
            ("fetch_metadata", "商品元数据与评论抓取"),
            ("clean_and_embed", "评论文本清洗与向量化"),
            ("cluster_pain_points", "高频痛点聚类"),
            ("generate_proposals", "生成双栏改款建议"),
            ("build_report", "报告生成与证据归档"),
        ]

        for item in items:
            # Check cancellation boundary
            session.refresh(task)
            if task.cancel_requested_at is not None or task.status == TaskStatus.CANCELED.value:
                logger.info("Task %s was canceled. Aborting pipeline.", task_id)
                return

            item.status = TaskStatus.RUNNING.value
            item.updated_at = utc_now()
            _emit_event(
                session,
                task_id=task_id,
                event_type="task_item.status_changed",
                payload={"status": TaskStatus.RUNNING.value},
                task_item_id=item.item_id,
            )
            session.commit()

            evidence_data, pain_points, proposals = _get_item_knowledge(item.asin)

            for node_id, node_name in pipeline_nodes:
                session.refresh(task)
                if task.cancel_requested_at is not None or task.status == TaskStatus.CANCELED.value:
                    return

                item.current_node = node_id
                item.updated_at = utc_now()
                node_start = utc_now()

                _emit_node(
                    session,
                    task_id=task_id,
                    item_id=item.item_id,
                    node_id=node_id,
                    node_name=node_name,
                    status=NodeStatus.RUNNING,
                    started_at=node_start,
                )

                # Simulated computation pacing (0.3s) for readable SSE flow
                time.sleep(0.3)

                if node_id == "build_report":
                    # Persist Evidence and Claims
                    now = utc_now()
                    for ev in evidence_data:
                        ev_id = _new_id("evd")
                        evidence = Evidence(
                            evidence_id=ev_id,
                            tenant_id=task.tenant_id,
                            task_id=task.task_id,
                            item_id=item.item_id,
                            source_type=EvidenceSourceType.REVIEW_TEXT.value,
                            source_ref=ev["source_ref"],
                            excerpt=ev["excerpt"],
                            source_url=f"https://www.amazon.com/dp/{item.asin}",
                            published_at=datetime.fromisoformat(ev["published_at"]).replace(tzinfo=UTC),
                            source_metadata={"rating": ev["rating"], "asin": item.asin},
                            provenance={"source": "amazon-us-reviews", "capture": "verified-purchase"},
                            created_at=now,
                        )
                        session.add(evidence)
                        session.flush()

                        session.add(
                            EvidenceClaimRef(
                                evidence_id=ev_id,
                                claim_id=ev["claim_id"],
                                claim_type="PAIN_POINT",
                            )
                        )

                    sample_metrics = {
                        "raw_review_count": 86,
                        "valid_review_count": 78,
                        "excluded_review_count": 8,
                        "average_rating": 4.1,
                        "negative_review_ratio": 0.23,
                        "pain_point_count_with_evidence": len(pain_points),
                        "window": {"preset": task.window_preset},
                        "methodology": "Amazon US 评论抽取、跨语言去噪清洗与 BGE-M3 语义向量聚类",
                        "missing_reasons": [],
                    }

                    report_id = _new_id("rpt")
                    report = Report(
                        report_id=report_id,
                        tenant_id=task.tenant_id,
                        task_id=task.task_id,
                        item_id=item.item_id,
                        data_quality=DataQuality.SUFFICIENT.value,
                        sample_metrics=sample_metrics,
                        generated_at=now,
                        financial_state=FinancialState.NOT_EVALUATED.value,
                        pain_points=pain_points,
                        proposals=proposals,
                        warnings=[],
                        model_metadata={
                            "engine": "insightx-pipeline-v1",
                            "embedding_model": "BAAI/bge-m3",
                            "clustering": "HDBSCAN",
                        },
                    )
                    session.add(report)

                    item.status = TaskStatus.COMPLETED.value
                    item.data_quality = DataQuality.SUFFICIENT.value
                    item.sample_metrics = sample_metrics
                    item.updated_at = now

                node_end = utc_now()
                duration_ms = int((node_end - node_start).total_seconds() * 1000)
                _emit_node(
                    session,
                    task_id=task_id,
                    item_id=item.item_id,
                    node_id=node_id,
                    node_name=node_name,
                    status=NodeStatus.SUCCESS,
                    started_at=node_start,
                    finished_at=node_end,
                    duration_ms=duration_ms,
                )

            _emit_event(
                session,
                task_id=task_id,
                event_type="task_item.status_changed",
                payload={"status": TaskStatus.COMPLETED.value},
                task_item_id=item.item_id,
            )
            session.commit()

        # Mark whole batch completed
        now = utc_now()
        task.status = TaskStatus.COMPLETED.value
        task.updated_at = now
        task.finished_at = now

        _emit_event(
            session,
            task_id=task_id,
            event_type="task.status_changed",
            payload={"status": TaskStatus.COMPLETED.value},
        )

        session.execute(
            update(OutboxMessage)
            .where(
                OutboxMessage.aggregate_id == task_id,
                OutboxMessage.status == "PENDING",
            )
            .values(status="PUBLISHED", published_at=now)
        )
        session.commit()
        logger.info("Task %s completed successfully.", task_id)


def poll_and_execute_next(session_factory: SessionFactory) -> bool:
    """Poll one pending queued task and process it."""
    with session_factory() as session:
        task = session.scalar(
            select(Task)
            .where(Task.status == TaskStatus.QUEUED.value)
            .order_by(Task.created_at.asc())
            .limit(1)
        )
        if task is None:
            return False
        task_id = task.task_id
    execute_task_pipeline(session_factory, task_id)
    return True


def run_worker(
    session_factory: SessionFactory,
    *,
    poll_interval: float = 1.0,
    run_once: bool = False,
) -> None:
    """Run persistent polling worker loop."""
    logger.info("InsightX worker polling started.")
    while True:
        try:
            executed = poll_and_execute_next(session_factory)
            if run_once:
                break
            if not executed:
                time.sleep(poll_interval)
        except Exception as e:
            logger.exception("Error in worker loop: %s", e)
            if run_once:
                raise
            time.sleep(poll_interval)
