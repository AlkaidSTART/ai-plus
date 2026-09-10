"""应用冒烟测试。"""


def test_health_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unimplemented_route_uses_error_envelope(client) -> None:
    resp = client.get("/api/v1/insight/tasks")
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "NOT_IMPLEMENTED"
