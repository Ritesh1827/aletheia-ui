"""Smoke tests for M1 Verify pages."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.verify import VERDICT_CAVEAT


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_search_renders(client: TestClient) -> None:
    res = client.get("/verify")
    assert res.status_code == 200
    assert "Serial lookup" in res.text
    assert "demo data" in res.text.lower()


def test_verified_detail(client: TestClient) -> None:
    res = client.get("/verify/TT-DEMO-0001", follow_redirects=False)
    assert res.status_code == 200
    assert "VERIFIED" in res.text
    assert VERDICT_CAVEAT in res.text
    assert "100% genuine" not in res.text


def test_clone_detail_shows_evidence(client: TestClient) -> None:
    res = client.get("/verify/TT-DEMO-0002", follow_redirects=False)
    assert res.status_code == 200
    assert "CLONE DETECTED" in res.text
    assert "R-VELOCITY-04" in res.text


def test_unknown_serial_state(client: TestClient) -> None:
    res = client.get("/verify/NOPE-123", follow_redirects=False)
    assert res.status_code == 404
    assert "Unknown serial" in res.text


def test_backend_error_state(client: TestClient) -> None:
    res = client.get("/verify/TT-DEMO-ERR", follow_redirects=False)
    assert res.status_code == 502
    assert "not an all-clear" in res.text


def test_search_redirects_known_serial(client: TestClient) -> None:
    res = client.get("/verify", params={"q": "TT-DEMO-0001"}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/verify/TT-DEMO-0001"


def test_bundle_download(client: TestClient) -> None:
    res = client.get("/verify/TT-DEMO-0001/bundle")
    assert res.status_code == 200
    assert res.json()["serial"] == "TT-DEMO-0001"
    assert "DEMO DATA" in res.json()["_demo_notice"]
