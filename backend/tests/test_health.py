"""应用冒烟测试。"""


def test_health_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stubbed_routes_keep_error_envelope(client) -> None:
    """报告仍为 501 占位；SSE 已在阶段 04 实现（需库），此处只断言其 UUID 校验（离线）。"""
    import uuid as uuid_mod

    task_id = str(uuid_mod.uuid4())
    item_id = str(uuid_mod.uuid4())
    resp = client.get(f"/api/v1/insight/task/{task_id}/items/{item_id}/report")
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "NOT_IMPLEMENTED"
    malformed = client.get("/api/v1/insight/task/not-a-uuid/events?after=0")
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "INVALID_INPUT"
