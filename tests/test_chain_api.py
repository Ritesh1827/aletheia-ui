"""Mapping tests: chain backend payload -> UI models (no network)."""

from __future__ import annotations

import pytest

from app.services import chain_api
from app.services.mock_verify import UnknownSerialError


class _Resp:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def _fake_get_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    verdict = {
        "serial": "LIVE-1",
        "verdict": "CLONE_DETECTED",
        "display": "Contested: conflicting histories",
        "risk_score": 65,
        "confidence": "high",
        "product": {"lot_id": "LOT-X", "status": "ACTIVE", "custodian": "did:t1"},
        "checks": [
            {"id": "LOT_COMMITMENT", "status": "pass", "evidence": {}},
            {"id": "R04", "status": "fail", "severity": "critical",
             "reason": "Seen 1148km apart", "evidence_refs": ["0xabc123def456"],
             "next_step": "Quarantine unit"},
        ],
        "uncertainty": ["Only 2 observations"],
        "next_steps": ["Quarantine unit"],
        "proofs": {},
    }
    bundle = {"events": [
        {"event_hash": "0xabc123def456", "serial": "LIVE-1", "type": "SCAN",
         "actor": "did:t1", "ts": 1700000000, "lat_mdeg": 19070, "lon_mdeg": 72870,
         "biz_step": "shipping"},
        {"event_hash": "0xdef456abc123", "serial": "LIVE-1", "type": "HANDOVER_ACCEPT",
         "actor": "did:t1", "ts": 1700000600, "lat_mdeg": None, "lon_mdeg": None,
         "biz_step": "receiving"},
    ], "lot_proof": {"status": "pass", "root": "0xbeef", "proof": []}}
    anchor = {"anchored": True, "anchor_id": 3, "root": "0xaaa",
              "tx": "0xbbb", "block": 370,
              "lot": {"status": "pass", "root": "0xbeef", "proof": []}}

    def fake_get(url: str, timeout: float = 15.0) -> _Resp:
        if url.endswith("/verify"):
            return _Resp(verdict)
        if url.endswith("/bundle"):
            return _Resp(bundle)
        if url.endswith("/anchor"):
            return _Resp(anchor)
        raise AssertionError(url)

    monkeypatch.setattr(chain_api.httpx, "get", fake_get)


def test_live_verdict_maps_to_ui_models(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_get_factory(monkeypatch)
    v = chain_api.verify_serial("LIVE-1")
    assert v.verdict == "CLONE_DETECTED"
    assert v.risk_score == 65
    assert v.identity.lot_id == "LOT-X"
    assert any(c.id == "R04" and c.status == "fail" for c in v.checks)
    assert v.findings and v.findings[0].severity == "critical"
    assert len(v.timeline) == 2
    assert v.timeline[1].kind == "custody"
    assert v.proof is not None and v.proof.proof_status == "PROOF VALID"
    assert v.proof.transaction_hash == "0xbbb"


def test_unknown_serial_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float = 15.0) -> _Resp:
        return _Resp({"verdict": "UNKNOWN", "display": "Unknown serial"})
    monkeypatch.setattr(chain_api.httpx, "get", fake_get)
    with pytest.raises(UnknownSerialError):
        chain_api.verify_serial("NOPE-1")


def test_chain_down_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, timeout: float = 15.0) -> _Resp:
        raise ConnectionError("down")
    monkeypatch.setattr(chain_api.httpx, "get", boom)
    with pytest.raises(chain_api.ChainUnavailableError):
        chain_api.verify_serial("LIVE-1")
