"""UI role gate: switch persists cookie, verifier blocked, operator flows."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_role_switch_sets_cookie(client: TestClient) -> None:
    r = client.post("/session/role", data={"role": "operator", "next": "/lots"},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code
    assert "tt_role=operator" in r.headers["set-cookie"]
    assert r.headers["location"] == "/lots"


def test_role_switch_rejects_open_redirect(client: TestClient) -> None:
    r = client.post("/session/role", data={"role": "operator", "next": "https://evil.example"},
                    follow_redirects=False)
    assert r.headers["location"] == "/"


def test_verifier_freeze_blocked_with_403_page(client: TestClient) -> None:
    r = client.post("/lots/LOT-DEMO-A/freeze",
                    data={"confirm": "LOT-DEMO-A", "reason": "x"})
    assert r.status_code == 403, r.status_code
    assert "Operator role required" in r.text


def test_operator_mock_freeze_flows(client: TestClient) -> None:
    r = client.post("/lots/LOT-DEMO-A/freeze?as=operator",
                    data={"confirm": "LOT-DEMO-A", "reason": "x"},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code


def test_detail_hides_actions_for_verifier(client: TestClient) -> None:
    r = client.get("/lots/LOT-DEMO-A")
    assert r.status_code == 200
    assert "Read-only role" in r.text
    assert "Confirm recall" not in r.text


def test_detail_shows_actions_for_operator(client: TestClient) -> None:
    r = client.get("/lots/LOT-DEMO-A?as=operator")
    assert r.status_code == 200
    assert "Confirm recall" in r.text
