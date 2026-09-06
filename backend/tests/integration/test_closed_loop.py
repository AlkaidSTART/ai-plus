"""Minimal closed-loop proof: Task → LangGraph → Events → Final Report.

Runs entirely offline against the in-memory runtime.
"""

import os

os.environ.setdefault("SSE_HEARTBEAT_SECONDS", "0.2")

import httpx
import pytest
from httpx import ASGITransport

from main import create_app


async def test_closed_loop_task_to_report():
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as client:
        # 1. create task
        resp = await client.post(
            "/api/v1/insight/tasks",
            json={
                "asins": ["B0C1234ABC"],
                "financial_constraint": {
                    "mold_cost_usd": 8000,
                    "moq": 1000,
                    "current_gross_margin": 0.32,
                    "expected_price_usd": 29.99,
                    "unit_cost_increase_usd": 1.8,
                },
            },
        )
        assert resp.status_code == 200
        task_id = resp.json()["data"]["tasks"][0]["task_id"]

        # 2. consume SSE until terminal
        import json

        events: list[dict] = []
        data_lines: list[str] = []
        async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as stream:
            assert stream.headers["content-type"].startswith("text/event-stream")
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    data_lines.append(line[6:])
                elif line == "" and data_lines:
                    events.append(json.loads("".join(data_lines)))
                    data_lines = []
                    if events[-1]["step"] in ("COMPLETED", "FAILED"):
                        break

        # 3. task reaches COMPLETED with a full final report
        assert events[-1]["step"] == "COMPLETED"
        detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
        assert detail["status"] == "COMPLETED"
        assert detail["progress"] == 100

        runtime = app.state.runtime
        final_task = await runtime.task_store.get(task_id)
        report = final_task.final_report
        assert report is not None
        assert report["task_id"] == task_id
        assert report["summary"]["review_count"] > 0
        assert len(report["clusters"]) == 5
        assert len(report["proposals"]) > 0
        assert all(p["status"] == "PASSED" for p in report["proposals"])
        assert len(report["evidence_links"]) == len(report["proposals"])
