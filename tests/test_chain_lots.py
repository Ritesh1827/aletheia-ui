"""Phase 4: live lots wiring (list/detail/blast/recall via mocked HTTP)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class FakeResp:
    def __init__(self, status: int, payload: dict | list | None = None):
        self.status_code = status
        self._payload = payload or {}

    def json(self) -> dict | list:
        assert self.status_code < 400
        return self._payload


LOTS_PAYLOAD = {"lots": [
    {"lot_id": "SHOW", "gtin": "GTIN-9", "size": 5, "root": "0xrr",
     "tx": "0xtt", "frozen": False, "units": 5,
     "by_status": {"ACTIVE": 4, "SOLD": 1}},
    {"lot_id": "OLD", "gtin": None, "size": 2, "root": "0xoo",
     "tx": "0xto", "frozen": True, "units": 2, "by_status": {"FROZEN": 2}},
]}

DETAIL_PAYLOAD = {
    "lot_id": "SHOW", "gtin": "GTIN-9", "size": 5, "root": "0xrr",
    "tx": "0xtt", "frozen": False,
    "units": [
        {"serial": "SHOW-000001", "status": "ACTIVE", "custodian": "did:maker1"},
        {"serial": "SHOW-000002", "status": "SOLD", "custodian": "did:retailer1"},
    ],
    "custodians": ["did:maker1", "did:retailer1"],
}

BLAST_PAYLOAD = {
    "lot": "SHOW", "total_units": 2, "by_status": {"ACTIVE": 1, "SOLD": 1},
    "invented_attempts": 0, "produced": 2, "overflow": False,
    "by_custodian": [], "claimed_units": 0,
    "tree": [{"pallet_id": "P-1", "cases": [
        {"case_id": "C-1", "units": [
            {"serial": "SHOW-000001", "status": "ACTIVE", "custodian": "did:maker1"},
            {"serial": "SHOW-000002", "status": "SOLD", "custodian": "did:retailer1"},
        ]}]}],
}


@pytest.fixture()
def chain_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.services import chain_api

    routes = {
        "/lots": FakeResp(200, LOTS_PAYLOAD),
        "/lots/SHOW": FakeResp(200, DETAIL_PAYLOAD),
        "/lots/SHOW/blast-radius": FakeResp(200, BLAST_PAYLOAD),
        "/lots/NOPE": FakeResp(404),
    }

    def fake_get(url: str, timeout: float = 15.0) -> FakeResp:
        path = url.split("http://test")[1]
        return routes.get(path, FakeResp(404))

    def fake_post(url: str, headers: dict | None = None, timeout: float = 20.0) -> FakeResp:
        assert url.endswith("/lots/SHOW/recall")
        assert (headers or {}).get("X-Role") == "operator", headers
        return FakeResp(200, {"lot": "SHOW", "frozen": True})

    monkeypatch.setenv("TRUSTTRACE_API_MODE", "chain")
    monkeypatch.setenv("TRUSTTRACE_CHAIN_API", "http://test")
    monkeypatch.setattr(chain_api.httpx, "get", fake_get)
    monkeypatch.setattr(chain_api.httpx, "post", fake_post)
    return TestClient(create_app(), raise_server_exceptions=False)


def test_chain_lots_list_and_filter(chain_client: TestClient) -> None:
    r = chain_client.get("/lots")
    assert r.status_code == 200
    assert "SHOW" in r.text and "OLD" in r.text
    r = chain_client.get("/lots", params={"freeze": "frozen"})
    assert "OLD" in r.text and "SHOW" not in r.text


def test_chain_lot_detail_and_blast(chain_client: TestClient) -> None:
    r = chain_client.get("/lots/SHOW")
    assert r.status_code == 200
    assert "SHOW-000001" in r.text
    r = chain_client.get("/lots/SHOW/blast-radius")
    assert r.status_code == 200
    assert "Pallet P-1" in r.text and "SHOW-000002" in r.text


def test_chain_lot_unknown(chain_client: TestClient) -> None:
    assert chain_client.get("/lots/NOPE").status_code == 404
    assert chain_client.get("/lots/LOT-DEMO-A").status_code == 200  # fixture preserved


def test_chain_recall(chain_client: TestClient) -> None:
    r = chain_client.post("/lots/SHOW/recall?as=operator",
                          data={"reason": "demo", "confirm": "SHOW"},
                          follow_redirects=False)
    assert r.status_code == 303, r.status_code
    assert "notice=recalled" in r.headers["location"]
