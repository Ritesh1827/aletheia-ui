"""Tests for Lots & Recall."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import mock_lots


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    mock_lots.reset_demo_state()


def test_lots_home_lists_inventory(client: TestClient) -> None:
    res = client.get("/lots")
    assert res.status_code == 200
    assert "Lots & Recall" in res.text
    assert "LOT-DEMO-A" in res.text
    assert "LOT-DEMO-B" in res.text
    assert "demo data" in res.text.lower()


def test_lots_search_filters(client: TestClient) -> None:
    res = client.get("/lots", params={"q": "LOT-DEMO-B"})
    assert res.status_code == 200
    assert "LOT-DEMO-B" in res.text
    assert "LOT-DEMO-A" not in res.text


def test_lots_empty_search_state(client: TestClient) -> None:
    res = client.get("/lots", params={"q": "LOT-NOPE"})
    assert res.status_code == 200
    assert "No lots match" in res.text


def test_lots_error_state(client: TestClient) -> None:
    res = client.get("/lots", params={"fail": "1"})
    assert res.status_code == 502
    assert "not an all-clear" in res.text


def test_lot_detail_renders(client: TestClient) -> None:
    res = client.get("/lots/LOT-DEMO-A")
    assert res.status_code == 200
    assert "LOT-DEMO-A" in res.text
    assert "AL-DEMO-0001" in res.text
    assert "INC-1042" in res.text
    assert "Blast radius" in res.text


def test_lot_detail_empty_products(client: TestClient) -> None:
    res = client.get("/lots/LOT-DEMO-B")
    assert res.status_code == 200
    assert "No product-level records" in res.text


def test_lot_unknown_is_404(client: TestClient) -> None:
    res = client.get("/lots/LOT-NOPE")
    assert res.status_code == 404
    assert "Unknown lot" in res.text


def test_blast_radius_partial_counts(client: TestClient) -> None:
    res = client.get("/lots/LOT-DEMO-A/blast-radius")
    assert res.status_code == 200
    assert "partial trace" in res.text
    assert "Only 2 of 10,000" in res.text
    assert "/verify/AL-DEMO-0002" in res.text
    assert "/incidents/INC-1042" in res.text
    assert "unlocated in demo" in res.text.lower()


def test_blast_radius_unknown_state(client: TestClient) -> None:
    res = client.get("/lots/LOT-DEMO-B/blast-radius")
    assert res.status_code == 200
    assert "unknown trace" in res.text
    assert "Nothing to trace yet" in res.text


def test_freeze_confirms_and_updates_state(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                      data={"confirm": "LOT-DEMO-A", "reason": "test hold"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert "FROZEN" in res.text
    assert "test hold" in res.text


def test_freeze_wrong_confirmation_rejected(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                      data={"confirm": "WRONG-ID", "reason": "x"})
    assert res.status_code == 422
    assert "no action taken" in res.text.lower()
    assert mock_lots._FROZEN.get("LOT-DEMO-A") is None


def test_freeze_is_idempotent(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                data={"confirm": "LOT-DEMO-A"})
    res = client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                      data={"confirm": "LOT-DEMO-A"},
                      follow_redirects=False)
    assert res.status_code == 303
    detail = mock_lots.get_lot("LOT-DEMO-A")
    assert detail.freeze_state == "frozen"
    assert detail.audit[-1].outcome.startswith("already-frozen")


def test_recall_freezes_and_audits(client: TestClient) -> None:
    res = client.post("/lots/LOT-DEMO-B/recall", params={"as": "admin"},
                      data={"confirm": "LOT-DEMO-B", "reason": "test recall"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert "RECALLED" in res.text
    detail = mock_lots.get_lot("LOT-DEMO-B")
    assert detail.recall_state == "recalled"
    assert detail.freeze_state == "frozen"
    assert any("test recall" in a.reason for a in detail.audit)


def test_audit_json_labelled_demo(client: TestClient) -> None:
    client.post("/lots/LOT-DEMO-A/freeze", params={"as": "investigator"},
                data={"confirm": "LOT-DEMO-A"})
    res = client.get("/lots/LOT-DEMO-A/audit")
    assert res.status_code == 200
    assert res.json()["lot_id"] == "LOT-DEMO-A"
    assert "DEMO DATA" in res.json()["_demo_notice"]


def test_existing_pages_still_work(client: TestClient) -> None:
    for path in ["/verify", "/verify/AL-DEMO-0001", "/overview", "/incidents",
                 "/incidents/INC-1042", "/explorer", "/red-team"]:
        res = client.get(path)
        assert res.status_code == 200, path
