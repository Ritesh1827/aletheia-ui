"""Tests for the Provenance Block Explorer."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import deps
from app.services.mock_explorer import TX_A, TX_B, TX_C


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_explorer_home_renders(client: TestClient) -> None:
    res = client.get("/explorer")
    assert res.status_code == 200
    assert "Provenance Explorer" in res.text
    assert "Inspect anchored supply-chain evidence, not token prices." in res.text
    assert "ANCH-DEMO-2" in res.text
    assert "demo" in res.text.lower()


def test_explorer_search_single_hit(client: TestClient) -> None:
    res = client.get("/explorer/search", params={"q": "1845517"})
    assert res.status_code == 200
    assert "1845517" in res.text


def test_explorer_search_no_match(client: TestClient) -> None:
    res = client.get("/explorer/search", params={"q": "nope-zzz-000"})
    assert res.status_code == 200
    assert "No matches" in res.text


def test_block_detail_renders(client: TestClient) -> None:
    res = client.get("/explorer/block/1845517")
    assert res.status_code == 200
    assert "Block 1845517" in res.text
    assert "anchorBatch" in res.text
    assert "gas" not in res.text.lower() or "Gas fields are omitted" in res.text


def test_block_unknown_is_404(client: TestClient) -> None:
    res = client.get("/explorer/block/9999999")
    assert res.status_code == 404
    assert "Unknown record" in res.text


def test_tx_detail_renders_with_proof(client: TestClient) -> None:
    res = client.get(f"/explorer/tx/{TX_B}")
    assert res.status_code == 200
    assert "anchorBatch" in res.text
    assert "Merkle proof" in res.text
    assert "NOT VERIFIED" in res.text


def test_tx_verify_runs_and_reports(client: TestClient) -> None:
    res = client.get(f"/explorer/tx/{TX_B}", params={"verify": "1"})
    assert res.status_code == 200
    assert "PROOF VALID" in res.text
    assert "Computed root matches" in res.text or "computed root" in res.text.lower()


def test_tx_pending_is_partial_evidence(client: TestClient) -> None:
    res = client.get(f"/explorer/tx/{TX_C}")
    assert res.status_code == 200
    assert "Partial evidence" in res.text
    assert "NOT VERIFIED" in res.text


def test_tx_unknown_is_404(client: TestClient) -> None:
    res = client.get("/explorer/tx/0xdeadbeef")
    assert res.status_code == 404
    assert "Unknown record" in res.text


def test_proof_json_unverified_then_verified(client: TestClient) -> None:
    plain = client.get(f"/explorer/tx/{TX_A}/proof")
    assert plain.status_code == 200
    assert plain.json()["status"] == "NOT VERIFIED"
    assert plain.json()["computed_root"] == ""
    verified = client.get(f"/explorer/tx/{TX_A}/proof", params={"verify": "1"})
    assert verified.status_code == 200
    assert verified.json()["status"] == "PROOF VALID"
    assert verified.json()["computed_root"] == verified.json()["expected_root"]


def test_tampered_vector_is_invalid() -> None:
    proof = deps.get_tampered_proof_demo()
    assert proof.status == "PROOF INVALID"
    assert proof.computed_root != proof.expected_root


def test_missing_payload_is_not_verified() -> None:
    proof = deps.get_merkle_proof(TX_C, verify=True)
    assert proof.status == "NOT VERIFIED"
    assert proof.leaf == ""


def test_address_renders(client: TestClient) -> None:
    from app.services.mock_explorer import CONTRACT

    res = client.get(f"/explorer/address/{CONTRACT}")
    assert res.status_code == 200
    assert "Provenance registry" in res.text


def test_address_unknown_is_404(client: TestClient) -> None:
    res = client.get("/explorer/address/0x0000000000000000000000000000000000000000")
    assert res.status_code == 404


def test_explorer_down_mode(client: TestClient) -> None:
    res = client.get("/explorer", params={"mode": "down"})
    assert res.status_code == 200
    assert "Disconnected" in res.text


def test_explorer_stale_mode(client: TestClient) -> None:
    res = client.get("/explorer", params={"mode": "stale"})
    assert res.status_code == 200
    assert "Stale" in res.text


def test_explorer_error_mode(client: TestClient) -> None:
    res = client.get("/explorer", params={"mode": "error"})
    assert res.status_code == 502
    assert "not an all-clear" in res.text


def test_existing_pages_still_work(client: TestClient) -> None:
    for path in ["/verify", "/verify/AL-DEMO-0001", "/incidents",
                 "/incidents/INC-1042", "/overview"]:
        res = client.get(path)
        assert res.status_code == 200, path
