"""Tests for the Red-Team Lab."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import deps
from app.services.mock_explorer import ACTOR_UNKNOWN, TX_B
from app.services.mock_redteam import InvalidScenarioInputError, UnknownScenarioError


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_lab_home_lists_scenarios(client: TestClient) -> None:
    res = client.get("/red-team")
    assert res.status_code == 200
    assert "Red-Team Lab" in res.text
    assert "demo data" in res.text.lower()
    for name in ["Clone QR", "revoked actor", "Fake handover", "tampering",
                 "Double claim", "Post-sale scan"]:
        assert name in res.text, name


def test_lab_scenario_page_renders_form(client: TestClient) -> None:
    res = client.get("/red-team/clone-qr")
    assert res.status_code == 200
    assert "Run scenario" in res.text
    assert "gap_minutes" in res.text


def test_lab_unknown_scenario_is_404(client: TestClient) -> None:
    res = client.get("/red-team/nope")
    assert res.status_code == 404
    assert "Unknown scenario" in res.text


def test_clone_qr_detected(client: TestClient) -> None:
    res = client.post("/red-team/clone-qr/run", params={"as": "operator"},
                      data={"serial": "AL-DEMO-0002", "gap_minutes": "41"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert "DETECTED" in res.text
    assert "R-VELOCITY-04" in res.text
    assert "evt-0012" in res.text
    assert "/verify/AL-DEMO-0002" in res.text
    assert "/incidents/INC-1042" in res.text


def test_clone_qr_clean_on_plausible_gap() -> None:
    result = deps.run_redteam_scenario("clone-qr", {"serial": "AL-DEMO-0002",
                                                    "gap_minutes": "600"})
    assert result.outcome == "clean"
    assert result.triggered_rules == []


def test_revoked_actor_rejected() -> None:
    result = deps.run_redteam_scenario("revoked-actor",
                                       {"actor": ACTOR_UNKNOWN, "serial": "AL-DEMO-0002"})
    assert result.outcome == "rejected"
    assert result.triggered_rules == ["R-ACTOR-01"]
    assert "REJECTED" in result.summary


def test_revoked_actor_clean_for_registered() -> None:
    from app.services.mock_explorer import ACTOR_NORTHWIND

    result = deps.run_redteam_scenario("revoked-actor",
                                       {"actor": ACTOR_NORTHWIND, "serial": "AL-DEMO-0001"})
    assert result.outcome == "clean"


def test_fake_handover_rejected_without_acceptance() -> None:
    result = deps.run_redteam_scenario("fake-handover",
                                       {"serial": "AL-DEMO-0001", "receiver_accepted": "no"})
    assert result.outcome == "rejected"
    assert result.triggered_rules == ["R-CUSTODY-03"]


def test_fake_handover_clean_with_acceptance() -> None:
    result = deps.run_redteam_scenario("fake-handover",
                                       {"serial": "AL-DEMO-0001", "receiver_accepted": "yes"})
    assert result.outcome == "clean"


def test_tampered_history_detected_with_values() -> None:
    result = deps.run_redteam_scenario("tampered-history", {"tx": TX_B})
    assert result.outcome == "detected"
    assert result.triggered_rules == ["R-CHAIN-02"]
    assert result.computed != result.expected
    assert result.explorer_link.endswith("?verify=1")


def test_double_claim_detected() -> None:
    result = deps.run_redteam_scenario(
        "double-claim",
        {"serial": "AL-DEMO-0002", "claimants": "Harbor Retail DC, Unknown claimant"})
    assert result.outcome == "detected"
    assert result.triggered_rules == ["R-DUP-IDENTITY-02"]
    assert result.incident_link == "/incidents/INC-1041"


def test_post_sale_scan_flagged() -> None:
    result = deps.run_redteam_scenario(
        "post-sale-scan",
        {"serial": "AL-DEMO-0001", "sale_event": "evt-0006", "scan_event": "evt-0007"})
    assert result.outcome == "flagged"
    assert result.triggered_rules == ["R-LIFECYCLE-05"]
    assert "evt-0006" in result.evidence_refs and "evt-0007" in result.evidence_refs


def test_invalid_scenario_id() -> None:
    with pytest.raises(UnknownScenarioError):
        deps.run_redteam_scenario("nope", {})


def test_malformed_inputs_rejected() -> None:
    with pytest.raises(InvalidScenarioInputError):
        deps.run_redteam_scenario("clone-qr", {"serial": "", "gap_minutes": "41"})
    with pytest.raises(InvalidScenarioInputError):
        deps.run_redteam_scenario("clone-qr", {"serial": "AL-DEMO-0002", "gap_minutes": "abc"})
    with pytest.raises(InvalidScenarioInputError):
        deps.run_redteam_scenario("double-claim", {"serial": "AL-DEMO-0002",
                                                   "claimants": "only-one"})
    with pytest.raises(InvalidScenarioInputError):
        deps.run_redteam_scenario("tampered-history", {"tx": "0xdead"})


def test_run_post_invalid_input_is_422(client: TestClient) -> None:
    res = client.post("/red-team/clone-qr/run", params={"as": "operator"},
                      data={"serial": "AL-DEMO-0002", "gap_minutes": "abc"})
    assert res.status_code == 422
    assert "must be a number" in res.text


def test_run_post_unknown_scenario_is_404(client: TestClient) -> None:
    res = client.post("/red-team/nope/run", params={"as": "operator"}, data={})
    assert res.status_code == 404


def test_result_json_endpoint(client: TestClient) -> None:
    res = client.get("/red-team/clone-qr/result", params={"as": "operator"})
    assert res.status_code == 422
    res = client.get("/red-team/nope/result", params={"as": "operator"})
    assert res.status_code == 404


def test_existing_pages_still_work(client: TestClient) -> None:
    paths = ["/verify", "/verify/AL-DEMO-0001", "/incidents",
             "/incidents/INC-1042", "/overview", "/explorer"]
    for path in paths:
        res = client.get(path)
        assert res.status_code == 200, path
