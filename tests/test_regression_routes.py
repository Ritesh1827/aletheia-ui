"""Regression tests: all core routes render through real templates + services.

Guards the early regression report: Verify/Incidents failing to load after the
Control Tower milestone. Every test below renders the actual Jinja template
against the real mock service — no bypasses.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.verify import VERDICT_CAVEAT


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_verify_search_loads(client: TestClient) -> None:
    res = client.get("/verify")
    assert res.status_code == 200
    assert "Serial lookup" in res.text
    assert "cmd-search" in res.text


def test_verify_detail_loads(client: TestClient) -> None:
    res = client.get("/verify/AL-DEMO-0001")
    assert res.status_code == 200
    assert "VERIFIED" in res.text
    assert "Check matrix" in res.text
    assert "Provenance timeline" in res.text
    assert VERDICT_CAVEAT in res.text


def test_incidents_list_loads(client: TestClient) -> None:
    res = client.get("/incidents")
    assert res.status_code == 200
    assert "All incidents" in res.text
    assert "INC-1042" in res.text


def test_incident_detail_loads(client: TestClient) -> None:
    res = client.get("/incidents/INC-1042")
    assert res.status_code == 200
    assert "Conflicting observations" in res.text
    assert "Evidence timeline" in res.text
    assert VERDICT_CAVEAT in res.text


def test_overview_loads(client: TestClient) -> None:
    res = client.get("/overview")
    assert res.status_code == 200
    assert "Control Tower" in res.text
    assert "Incident queue" in res.text


def test_unknown_serial_is_404_not_success(client: TestClient) -> None:
    res = client.get("/verify/NOPE-123")
    assert res.status_code == 404
    assert "Unknown serial" in res.text
    assert "VERIFIED" not in res.text


def test_backend_failure_is_502_not_success(client: TestClient) -> None:
    res = client.get("/verify/AL-DEMO-ERR")
    assert res.status_code == 502
    assert "not an all-clear" in res.text
    assert "VERIFIED" not in res.text


def test_unknown_case_is_404_not_success(client: TestClient) -> None:
    res = client.get("/incidents/INC-9999")
    assert res.status_code == 404
    assert "Unknown case" in res.text


def test_bad_action_is_404_page_not_500(client: TestClient) -> None:
    res = client.post("/incidents/INC-1042/actions", params={"as": "investigator", "action": "bogus"})
    assert res.status_code == 404
    assert "Unknown case" in res.text
    assert "Internal Server Error" not in res.text


def test_action_on_unknown_case_is_404_page_not_500(client: TestClient) -> None:
    res = client.post("/incidents/INC-9999/actions", params={"as": "investigator", "action": "note"})
    assert res.status_code == 404
    assert "Unknown case" in res.text


def test_bundle_failure_is_typed_error_not_verdict(client: TestClient) -> None:
    res = client.get("/verify/AL-DEMO-ERR/bundle")
    assert res.status_code == 502
    assert "verdict" not in res.json()
    assert res.json()["_demo_notice"].startswith("DEMO DATA")


def test_export_failure_is_typed_error(client: TestClient) -> None:
    res = client.get("/incidents/INC-9999/export")
    assert res.status_code == 404
    assert "error" in res.json()
