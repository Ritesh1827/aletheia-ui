"""Tests for Access Control: matrix, guards, demo session, spoof resistance."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import mock_access, mock_audit, mock_lots


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    mock_access.reset_demo_state()
    mock_audit.reset_demo_state()
    mock_lots.reset_demo_state()


def test_access_page_renders_matrix(client: TestClient) -> None:
    res = client.get("/access")
    assert res.status_code == 200
    assert "Permission matrix" in res.text
    assert "Read-only Verifier" in res.text
    assert "lot:freeze" in res.text
    assert "demo" in res.text.lower()
    assert "not identity verification" in res.text


def test_access_page_shows_current_session(client: TestClient) -> None:
    res = client.get("/access", params={"as": "admin"})
    assert res.status_code == 200
    assert "Acting as Admin" in res.text


def test_role_switch_sets_cookie_and_redirects(client: TestClient) -> None:
    res = client.post("/access/role", data={"role_id": "investigator", "next": "/access"},
                      follow_redirects=False)
    assert res.status_code == 303
    assert "al_role=investigator" in res.headers.get("set-cookie", "")
    follow = client.get("/access")
    assert "Acting as Investigator" in follow.text


def test_unknown_role_normalizes_to_verifier(client: TestClient) -> None:
    res = client.post("/access/role", data={"role_id": "superuser", "next": "/access"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert "Acting as Read-only Verifier" in res.text


def test_next_url_must_be_local(client: TestClient) -> None:
    res = client.post("/access/role",
                      data={"role_id": "admin", "next": "https://evil.example/"},
                      follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"].startswith("/access")


def test_verifier_denied_freeze(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-A/freeze", data={"confirm": "LOT-DEMO-A"})
    assert res.status_code == 403
    assert "lot:freeze" in res.text
    assert "403" in res.text


def test_verifier_denied_recall_annotate_and_redteam(client: TestClient) -> None:
    assert client.post("/lots/LOT-DEMO-B/recall",
                       data={"confirm": "LOT-DEMO-B"}).status_code == 403
    assert client.post("/incidents/INC-1042/actions",
                       params={"action": "note"}).status_code == 403
    assert client.post("/red-team/clone-qr/run",
                       data={"serial": "AL-DEMO-0002",
                             "gap_minutes": "41"}).status_code == 403
    res = client.get("/red-team/clone-qr/result")
    assert res.status_code == 403
    assert res.json()["error"].startswith("Role lacks permission")


def test_spoofed_unknown_role_cannot_escalate(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "root"},
                      data={"confirm": "LOT-DEMO-A"})
    assert res.status_code == 403


def test_investigator_can_freeze_but_not_recall(client: TestClient) -> None:
    ok = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                     data={"confirm": "LOT-DEMO-A"}, follow_redirects=False)
    assert ok.status_code == 303
    denied = client.post("/lots/LOT-DEMO-A/recall", params={"as": "investigator"},
                         data={"confirm": "LOT-DEMO-A"})
    assert denied.status_code == 403
    assert "lot:recall" in denied.text


def test_admin_can_recall(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-B/recall", params={"as": "admin"},
                      data={"confirm": "LOT-DEMO-B"}, follow_redirects=False)
    assert res.status_code == 303


def test_operator_least_privilege_for_redteam(client: TestClient) -> None:
    run = client.post("/red-team/clone-qr/run", params={"as": "operator"},
                      data={"serial": "AL-DEMO-0002", "gap_minutes": "41"},
                      follow_redirects=False)
    assert run.status_code == 303
    frozen = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "operator"},
                         data={"confirm": "LOT-DEMO-A"})
    assert frozen.status_code == 403


def test_cookie_session_persists_across_requests(client: TestClient) -> None:
    client.post("/access/role", data={"role_id": "admin", "next": "/access"})
    res = client.post("/lots/LOT-DEMO-B/recall", data={"confirm": "LOT-DEMO-B"},
                      follow_redirects=False)
    assert res.status_code == 303


def test_denial_names_permission_without_data_leak(client: TestClient) -> None:
    res = client.post("/incidents/INC-1042/actions", params={"action": "note"})
    assert res.status_code == 403
    assert "incident:annotate" in res.text
    assert "Read-only Verifier" in res.text


def test_denied_attempts_appear_in_access_audit(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", data={"confirm": "LOT-DEMO-A"})
    res = client.get("/access")
    assert "denied" in res.text
    assert "lot:freeze" in res.text
