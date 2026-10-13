"""Route and service tests for M2 (Control Tower + Incidents)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.verify import VERDICT_CAVEAT


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_overview_renders_metrics_and_queue(client: TestClient) -> None:
    res = client.get("/overview")
    assert res.status_code == 200
    assert "Control Tower" in res.text
    assert "Open critical incidents" in res.text
    assert "INC-1042" in res.text
    assert "demo data" in res.text.lower()


def test_overview_metric_links_to_filtered_queue(client: TestClient) -> None:
    res = client.get("/overview")
    assert "/incidents?severity=critical" in res.text


def test_overview_filter_empty_state(client: TestClient) -> None:
    res = client.get("/overview", params={"severity": "info", "status": "open"})
    assert res.status_code == 200
    assert "No incidents match these filters" in res.text


def test_overview_error_state(client: TestClient) -> None:
    res = client.get("/overview", params={"fail": "1"})
    assert res.status_code == 502
    assert "not an all-clear" in res.text


def test_incidents_list_links_to_detail(client: TestClient) -> None:
    res = client.get("/incidents")
    assert res.status_code == 200
    assert "/incidents/INC-1042" in res.text
    assert "/verify/TT-DEMO-0002" in res.text


def test_incident_detail_shows_conflict_and_timeline(client: TestClient) -> None:
    res = client.get("/incidents/INC-1042")
    assert res.status_code == 200
    assert "Conflicting observations" in res.text
    assert "R-VELOCITY-04" in res.text
    assert "Evidence timeline" in res.text
    assert VERDICT_CAVEAT in res.text
    assert "100% genuine" not in res.text


def test_incident_detail_unknown(client: TestClient) -> None:
    res = client.get("/incidents/INC-9999")
    assert res.status_code == 404
    assert "Unknown case" in res.text


def test_incident_detail_error_path(client: TestClient) -> None:
    res = client.get("/incidents/INC-ERR")
    assert res.status_code == 502
    assert "Correlation ID" in res.text


def test_incident_export_is_labelled_demo(client: TestClient) -> None:
    res = client.get("/incidents/INC-1042/export")
    assert res.status_code == 200
    assert res.json()["id"] == "INC-1042"
    assert "DEMO DATA" in res.json()["_demo_notice"]


def test_incident_action_redirects_with_notice(client: TestClient) -> None:
    res = client.post("/incidents/INC-1042/actions", params={"action": "note", "note": "checked seal"},
                      follow_redirects=False)
    assert res.status_code == 303
    assert "notice=noted" in res.headers["location"]
    follow = client.get(res.headers["location"])
    assert "Demo action recorded" in follow.text


def test_verify_page_unchanged(client: TestClient) -> None:
    res = client.get("/verify/TT-DEMO-0001", follow_redirects=False)
    assert res.status_code == 200
    assert "VERIFIED" in res.text
    assert VERDICT_CAVEAT in res.text
