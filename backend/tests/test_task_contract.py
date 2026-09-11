"""任务契约纯函数测试（离线，无数据库）：规范化、日期窗、幂等哈希、游标、错误包、OpenAPI。"""

import base64
import json
import uuid
from datetime import date

import pytest

from app.api.errors import ErrorCode, error_response
from app.api.schemas import Window
from app.main import create_app
from app.services import tasks as task_svc
from app.worker.nodes import NODE_ORDER

TODAY = date(2026, 9, 10)
TENANT = uuid.uuid5(uuid.NAMESPACE_URL, "contract/tenant")
PROJECT = uuid.uuid5(uuid.NAMESPACE_URL, "contract/project")


def test_normalize_asins():
    assert task_svc.normalize_asins(["b012345678", "B012345678", "B087654321"]) == [
        "B012345678",
        "B087654321",
    ]


def test_minus_calendar_months():
    assert task_svc.minus_calendar_months(date(2026, 9, 10), 6) == date(2026, 3, 10)
    assert task_svc.minus_calendar_months(date(2026, 8, 31), 6) == date(2026, 2, 28)
    assert task_svc.minus_calendar_months(date(2024, 8, 31), 6) == date(2024, 2, 29)


def test_resolve_window_default():
    assert task_svc.resolve_window(None, None, TODAY) == (date(2026, 3, 10), TODAY)


def test_resolve_window_explicit():
    assert task_svc.resolve_window(date(2026, 3, 10), TODAY, TODAY) == (
        date(2026, 3, 10),
        TODAY,
    )


def test_resolve_window_reversed():
    with pytest.raises(ValueError):
        task_svc.resolve_window(TODAY, date(2026, 3, 10), TODAY)


def test_resolve_window_future_end():
    with pytest.raises(ValueError):
        task_svc.resolve_window(date(2026, 9, 10), date(2026, 9, 11), TODAY)


def test_resolve_window_partial():
    with pytest.raises(ValueError):
        task_svc.resolve_window(date(2026, 3, 10), None, TODAY)


def _intent_hash(asins, window):
    intent = task_svc.canonical_intent(
        TENANT, PROJECT, asins, "amazon", "US", window
    )
    return task_svc.intent_hash(intent)


def test_intent_hash_stable_for_default_window_across_days():
    assert _intent_hash(["B012345678"], None) == _intent_hash(["B012345678"], None)
    assert task_svc.intent_hash(
        task_svc.canonical_intent(
            TENANT, PROJECT, ["B012345678"], "amazon", "US", None
        )
    ) == task_svc.intent_hash(
        task_svc.canonical_intent(
            TENANT, PROJECT, ["b012345678"], "amazon", "US", None
        )
    )


def test_intent_hash_differs_on_input():
    assert _intent_hash(["B012345678"], None) != _intent_hash(["B087654321"], None)
    assert _intent_hash(["B012345678"], None) != _intent_hash(
        ["B012345678"],
        Window(start_date=date(2026, 3, 10), end_date=TODAY),
    )


def test_cursor_roundtrip():
    created = __import__("datetime").datetime(2026, 9, 10, 8, 0, 0)
    task_id = uuid.uuid4()
    cursor = task_svc.encode_cursor(created, task_id, PROJECT, None)
    assert task_svc.decode_cursor(cursor, PROJECT, None) == (created, task_id)


def test_cursor_rejects_foreign_filter():
    cursor = task_svc.encode_cursor(
        __import__("datetime").datetime(2026, 9, 10, 8, 0, 0), uuid.uuid4(), PROJECT, None
    )
    with pytest.raises(ValueError):
        task_svc.decode_cursor(cursor, uuid.uuid4(), None)


@pytest.mark.parametrize(
    "bad",
    [
        "!!!",
        "e30",
        base64.urlsafe_b64encode(b"[1,2]").decode().rstrip("="),
        base64.urlsafe_b64encode(b'{"c":"x"}').decode().rstrip("="),
    ],
)
def test_cursor_rejects_garbage(bad):
    with pytest.raises(ValueError):
        task_svc.decode_cursor(bad, PROJECT, None)


def test_error_envelope_shape():
    resp = error_response(422, ErrorCode.INVALID_ASIN, "bad asin")
    body = json.loads(resp.body)
    assert resp.status_code == 422
    assert body["error"]["code"] == "INVALID_ASIN"
    assert body["error"]["message"] == "bad asin"
    assert body["error"]["details"] == []
    assert body["error"]["request_id"] == "req_todo"


def test_openapi_implemented_task_paths():
    paths = create_app().openapi()["paths"]
    assert set(paths["/api/v1/insight/task"].keys()) == {"post"}
    assert set(paths["/api/v1/insight/tasks"].keys()) == {"get"}
    assert set(paths["/api/v1/insight/task/{task_id}"].keys()) == {"get"}
    assert set(paths["/api/v1/insight/task/{task_id}/cancel"].keys()) == {"post"}
    assert set(paths["/api/v1/insight/task/{task_id}/retry"].keys()) == {"post"}
    assert "/api/v1/insight/task/{task_id}/events" in paths


def test_total_nodes_matches_seven_step_contract():
    assert task_svc.TOTAL_NODES == 7
    assert len(NODE_ORDER) == 7
