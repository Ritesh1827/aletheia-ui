"""Tests for Audit & Integrity: recording, verification, tamper detection."""

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


def test_audit_page_requires_permission(client: TestClient) -> None:
    denied = client.get("/audit")
    assert denied.status_code == 403
    assert "integrity:view" in denied.text
    allowed = client.get("/audit", params={"as": "investigator"})
    assert allowed.status_code == 200
    assert "Audit log" in allowed.text
    assert "NOT VERIFIED" not in allowed.text or "PASS" in allowed.text


def test_seeded_log_verifies_pass(client: TestClient) -> None:
    res = client.get("/audit", params={"as": "admin"})
    assert res.status_code == 200
    assert "PASS" in res.text
    assert "EVT-0001" in res.text


def test_empty_log_is_not_verified_not_pass() -> None:
    mock_audit._LOG.clear()
    report = mock_audit.verify()
    assert report.status == "NOT VERIFIED"
    assert report.checked == 0
    assert "PASS" not in report.status


def test_freeze_records_allowed_event_with_actor(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                data={"confirm": "LOT-DEMO-A", "reason": "hold for review"})
    entries = [e for e in mock_audit._LOG if e.action == "lot:freeze" and e.target == "LOT-DEMO-A"]
    assert entries, "freeze must append a unified audit event"
    last = entries[-1]
    assert last.actor == "demo.investigator"
    assert last.outcome == "allowed"
    assert last.record_hash and last.prev_hash


def test_freeze_reason_text_never_enters_unified_log(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                data={"confirm": "LOT-DEMO-A", "reason": "password=hunter2 secret"})
    blob = " ".join(
        f"{e.actor} {e.action} {e.target} {e.outcome} {e.context!r}" for e in mock_audit._LOG
    )
    assert "hunter2" not in blob


def test_incident_note_text_never_stored(client: TestClient) -> None:
    client.post("/incidents/INC-1042/actions",
                params={"as": "investigator", "action": "note", "note": "seal number XYZ-999 confidential"},
                follow_redirects=False)
    blob = " ".join(
        f"{e.actor} {e.action} {e.target} {e.outcome} {e.context!r}" for e in mock_audit._LOG
    )
    assert "XYZ-999" not in blob
    assert any(e.action == "incident:annotate" and e.outcome == "allowed"
               for e in mock_audit._LOG)


def test_denied_attempt_is_audited(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", data={"confirm": "LOT-DEMO-A"})
    denied = [e for e in mock_audit._LOG
              if e.action == "lot:freeze" and e.outcome == "denied"]
    assert denied, "denials must leave an audit trail"
    res = client.get("/audit", params={"as": "admin", "outcome": "denied"})
    assert res.status_code == 200
    assert "denied" in res.text


def test_tampered_record_detected_with_evidence() -> None:
    mock_audit.record("demo.admin", "lot:recall", "LOT-DEMO-B", "allowed", {})
    assert mock_audit.tamper_demo(2, "target", "LOT-EVIL") is True
    report = mock_audit.verify()
    assert report.status == "FAIL"
    assert report.failures, "FAIL must name evidence"
    assert any("altered record" in f.reason for f in report.failures)


def test_rewritten_history_breaks_the_link() -> None:
    mock_audit.record("demo.admin", "lot:recall", "LOT-DEMO-B", "allowed", {})
    assert mock_audit.tamper_demo(2, "target", "LOT-EVIL") is True
    resealed = next(e for e in mock_audit._LOG if e.seq == 2)
    resealed.record_hash = mock_audit._digest(mock_audit._canonical(resealed))
    report = mock_audit.verify()
    assert report.status == "FAIL"
    assert any("broken link" in f.reason for f in report.failures)


def test_tamper_unknown_seq_is_rejected() -> None:
    assert mock_audit.tamper_demo(999, "target", "X") is False
    assert mock_audit.verify().status == "PASS"


def test_redteam_run_and_role_switch_audited(client: TestClient) -> None:
    client.post("/red-team/clone-qr/run", params={"as": "operator"},
                data={"serial": "AL-DEMO-0002", "gap_minutes": "41"})
    client.post("/access/role", data={"role_id": "admin", "next": "/access"})
    actions = {(e.action, e.outcome) for e in mock_audit._LOG}
    assert ("redteam:run", "allowed") in actions
    assert ("session:switch-role", "allowed") in actions


def test_audit_filters(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", data={"confirm": "LOT-DEMO-A"})
    res = client.get("/audit", params={"as": "admin", "outcome": "denied"})
    assert res.status_code == 200
    assert "denied" in res.text
    res = client.get("/audit", params={"as": "admin", "action": "lot:freeze"})
    assert res.status_code == 200
    assert "lot:freeze" in res.text
