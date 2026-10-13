"""Live chain client: trust-fabric backend -> UI models.

Same typed interface as mock_verify (raises UnknownSerialError, never None).
Backend down -> ChainUnavailableError (route renders error state, never all-clear).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app import config
from app.models.verify import (
    AnchorProof,
    CheckResult,
    EvidenceFinding,
    ProductIdentity,
    ProvenanceEvent,
    VerificationVerdict,
)
from app.services.mock_verify import UnknownSerialError

CUSTODY_TYPES = {"MANUFACTURED", "HANDOVER_OFFER", "HANDOVER_ACCEPT", "SOLD"}

CHECK_LABELS = {
    "LOT_COMMITMENT": "Lot commitment",
    "CHAIN_INTEGRITY": "Chain integrity",
    "R01": "Identity uniqueness",
    "R02": "Seal / secret",
    "R03": "Lot inclusion",
    "R04": "Movement plausibility",
    "R05": "Quantity overflow",
    "R06": "Route order",
    "R07": "Custody sequence",
    "R08": "Actor authorization",
    "R09": "Integrity",
    "R11": "Lifecycle",
    "R12": "Lifecycle",
    "R13": "Tap counter",
    "R14": "Seal / device",
}

_SEV = {"critical": "critical", "high": "watch", "medium": "watch", "low": "info"}


class ChainUnavailableError(Exception):
    def __init__(self, correlation_id: str = "chain-unreachable") -> None:
        super().__init__("Chain backend unreachable")
        self.correlation_id = correlation_id


def _get(path: str) -> dict:
    base = config.chain_api_base().rstrip("/")
    try:
        r = httpx.get(f"{base}{path}", timeout=15.0)
    except Exception as exc:
        raise ChainUnavailableError() from exc
    if r.status_code == 404:
        raise UnknownSerialError(path)
    if r.status_code >= 500:
        raise ChainUnavailableError(correlation_id=f"chain-{r.status_code}")
    if r.status_code >= 400:
        # Backend rejection (bad input, throttled, any other 4xx): render the
        # honest error page, never a 500 and never an all-clear.
        raise ChainUnavailableError(correlation_id=f"chain-{r.status_code}")
    return r.json()


def _short(ref: str) -> str:
    return ref[:12] if isinstance(ref, str) and ref.startswith("0x") else str(ref)[:24]


def verify_serial(serial: str) -> VerificationVerdict:
    """Fetch live verdict + bundle + anchor, map to UI models."""
    key = serial.strip()
    if not key or len(key) > 128:
        # Matches the backend's serial cap: reject locally, no backend hit.
        raise UnknownSerialError(serial=key[:128])
    try:
        v = _get(f"/products/{key}/verify")
    except UnknownSerialError:
        raise
    if v.get("verdict") == "UNKNOWN":
        raise UnknownSerialError(serial=key)

    try:
        bundle = _get(f"/products/{key}/bundle")
    except (UnknownSerialError, ChainUnavailableError):
        bundle = {"events": [], "lot_proof": {}}
    try:
        anchor = _get(f"/products/{key}/anchor")
    except (UnknownSerialError, ChainUnavailableError):
        anchor = {"anchored": False}

    prod = v.get("product") or {}
    failed = [c for c in v.get("checks", []) if c.get("status") == "fail"]

    checks = []
    for c in v.get("checks", []):
        st = c.get("status", "unknown")
        checks.append(CheckResult(
            id=c.get("id", "?"),
            label=CHECK_LABELS.get(c.get("id", ""), c.get("id", "?")),
            status=st if st in ("pass", "fail", "warn") else "unknown",
            detail=(c.get("reason") or c.get("status", "") or "")[:300]
            or f"Check {c.get('id')} {st}.",
        ))

    findings = [
        EvidenceFinding(
            rule_id=c.get("id", "?"),
            severity=_SEV.get(c.get("severity", "low"), "info"),
            reason=c.get("reason", "")[:500],
            references=[_short(e) for e in c.get("evidence_refs", [])][:6],
            uncertainty="",
            next_step=(c.get("next_step", "") or "")[:300],
        )
        for c in failed
    ]

    timeline = []
    for e in (bundle.get("events") or [])[-12:]:
        ts = e.get("ts")
        when = (datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                if isinstance(ts, int) else "undated")
        lat, lon = e.get("lat_mdeg"), e.get("lon_mdeg")
        loc = f"{lat / 1000:.3f}, {lon / 1000:.3f}" if lat is not None and lon is not None else ""
        timeline.append(ProvenanceEvent(
            event_id=_short(e.get("event_hash", "?")),
            timestamp=when,
            kind="custody" if e.get("type") in CUSTODY_TYPES else "observation",
            actor=str(e.get("actor", "?"))[:48],
            summary=f"{e.get('type', '?')} · {e.get('biz_step', '')}"[:120],
            location=loc,
        ))

    lot = anchor.get("lot", {}) or bundle.get("lot_proof", {})
    proof = AnchorProof(
        anchor_id=str(anchor.get("anchor_id", "pending")),
        merkle_root=str(lot.get("root", "—"))[:66],
        transaction_hash=str(anchor.get("tx", "batch anchor pending"))[:66],
        block_height=int(anchor.get("block") or 0),
        proof_status="PROOF VALID" if lot.get("status") == "pass" and anchor.get("anchored") else "NOT VERIFIED",
        leaf_count=len(bundle.get("events", [])),
    )

    fails = "; ".join(c.get("reason", "") for c in failed)[:600]
    explanation = (v.get("display", "") + ". " + fails).strip()
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return VerificationVerdict(
        serial=key,
        verdict=v.get("verdict", "UNKNOWN"),
        explanation=explanation or v.get("display", ""),
        risk_score=int(v.get("risk_score", 0)),
        confidence=f"{v.get('confidence', '?').title()} — risk {v.get('risk_score', 0)}/100.",
        uncertainty="; ".join(v.get("uncertainty", []))[:300],
        retrieved_at=now,
        identity=ProductIdentity(
            serial=key,
            lot_id=str(prod.get("lot_id", "—")),
            product="Unit " + key,
            lifecycle_status=str(prod.get("status", "—")),
            permitted_custodian=str(prod.get("custodian", "—"))[:48],
        ),
        checks=checks,
        findings=findings,
        timeline=timeline,
        proof=proof,
    )


# ---- Live lots & recall (Phase 4) ----

from app.models.lots import (  # noqa: E402
    BlastNode,
    BlastRadius,
    LotAnchorRef,
    LotAuditEntry,
    LotDetail,
    LotProduct,
    LotSummary,
)
from app.services.mock_lots import LotsBackendError, UnknownLotError  # noqa: E402

_DEMO_LOT_IDS = {"LOT-DEMO-A", "LOT-DEMO-B", "LOT-ERR"}


def _lot_get(path: str, lot_id: str) -> dict:
    try:
        return _get(path)
    except UnknownSerialError:
        raise UnknownLotError(lot_id=lot_id) from None
    except ChainUnavailableError as exc:
        raise LotsBackendError(correlation_id=exc.correlation_id) from None


def list_lots(query: str = "", freeze: str = "all") -> list[LotSummary]:
    data = _lot_get("/lots", "?")
    out = []
    for l in data.get("lots", []):
        frozen = bool(l.get("frozen"))
        if freeze == "frozen" and not frozen:
            continue
        if freeze == "active" and frozen:
            continue
        if query and query.strip().upper() not in l.get("lot_id", "").upper():
            continue
        n_anchors = 1 if l.get("tx") else 0
        out.append(LotSummary(
            lot_id=l.get("lot_id", "?"),
            product=str(l.get("gtin") or l.get("lot_id", "?")),
            committed_qty=int(l.get("size") or l.get("units") or 0),
            freeze_state="frozen" if frozen else "active",
            # Backend recall freezes on-chain; freeze and recall share the flag.
            recall_state="recalled" if frozen else "none",
            anchor_state="anchored" if n_anchors else "pending",
            incidents_open=0,
        ))
    return out


def get_lot(lot_id: str) -> LotDetail:
    key = lot_id.strip()
    if not key or len(key) > 128:
        raise UnknownLotError(lot_id=key[:128])
    l = _lot_get(f"/lots/{key}", key)
    frozen = bool(l.get("frozen"))
    products = []
    for u in l.get("units", []):
        st = str(u.get("status", ""))
        products.append(LotProduct(
            serial=u.get("serial", "?"),
            status=st,
            custodian=str(u.get("custodian", ""))[:48],
            sale_state="sold" if st in ("SOLD", "CLAIMED") else "unsold",
        ))
    tx = l.get("tx")
    return LotDetail(
        lot_id=l.get("lot_id", key),
        product=str(l.get("gtin") or l.get("lot_id", key)),
        committed_qty=int(l.get("size") or len(products)),
        lifecycle="frozen" if frozen else "active",
        freeze_state="frozen" if frozen else "active",
        recall_state="recalled" if frozen else "none",
        permitted_custodians=[str(a)[:48] for a in l.get("custodians", [])],
        products=products,
        incidents=[],
        anchors=[LotAnchorRef(
            anchor_id=str(tx)[:24] if tx else "BATCH-PENDING",
            tx_hash=str(tx)[:66] if tx else None,
            root=str(l.get("root", ""))[:66],
            event_count=len(products),
            state="anchored" if tx else "pending",
        )],
        audit=[],
        updated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


_UNIT_TONE = {"CLAIMED": "good", "SOLD": "watch", "FROZEN": "neutral", "ACTIVE": "neutral"}


def get_blast_radius(lot_id: str) -> BlastRadius:
    key = lot_id.strip()
    if not key or len(key) > 128:
        raise UnknownLotError(lot_id=key[:128])
    b = _lot_get(f"/lots/{key}/blast-radius", key)
    by_status = b.get("by_status", {})
    sold = int(by_status.get("SOLD", 0)) + int(by_status.get("CLAIMED", 0))
    unsold = int(by_status.get("ACTIVE", 0))
    unlocated = int(b.get("invented_attempts", 0))
    overflow = bool(b.get("overflow"))
    tree = []
    for pallet in b.get("tree", []):
        pnodes = []
        for case in pallet.get("cases", []):
            leaves = [BlastNode(
                label=f"{u.get('serial')} · {str(u.get('status', '')).lower()}",
                detail=str(u.get("custodian", ""))[:64],
                link=f"/verify/{u.get('serial')}",
                tone=_UNIT_TONE.get(str(u.get("status", "")), "neutral"),  # type: ignore[arg-type]
            ) for u in case.get("units", [])]
            pnodes.append(BlastNode(
                label=f"Case {case.get('case_id')}" if case.get("case_id") else "Direct units",
                detail=f"{len(leaves)} units", tone="neutral", children=leaves,
            ))
        pid = pallet.get("pallet_id")
        tree.append(BlastNode(
            label=f"Pallet {pid}" if pid else "Unpackaged units",
            detail=f"{sum(len(c.children) for c in pnodes)} units",
            tone="neutral", children=pnodes,
        ))
    return BlastRadius(
        lot_id=b.get("lot", key),
        affected=int(b.get("total_units", 0)),
        sold=sold, unsold=unsold, unlocated=unlocated,
        completeness="partial" if overflow else "complete",
        completeness_note=(
            "Clone probes hit this lot without matching committed units — "
            "overflow scans recorded, all committed units traced."
            if overflow else
            "All committed units traced to pallets, cases, and custodians."
        ),
        tree=tree,
        incident_links=[],
    )


def _recall_entry(lot_id: str, action: str, reason: str, role: str = "verifier") -> LotAuditEntry:
    key = lot_id.strip()
    if not key or len(key) > 128:
        raise UnknownLotError(lot_id=key[:128])
    base = config.chain_api_base().rstrip("/")
    try:
        r = httpx.post(f"{base}/lots/{key}/recall", headers={"X-Role": role}, timeout=20.0)
    except Exception as exc:
        raise LotsBackendError(correlation_id="chain-unreachable") from exc
    if r.status_code == 404:
        raise UnknownLotError(lot_id=key)
    if r.status_code >= 400:
        raise LotsBackendError(correlation_id=f"chain-{r.status_code}")
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return LotAuditEntry(at=now, actor="chain", action=action,
                         outcome="recalled" if action == "recall" else "frozen",
                         reason=reason[:500])


def freeze_lot(lot_id: str, reason: str = "", role: str = "verifier") -> LotAuditEntry:
    # Backend recall freezes on-chain; freeze shares the effect (transfer hold).
    return _recall_entry(lot_id, "freeze", reason, role)


def recall_lot(lot_id: str, reason: str = "", role: str = "verifier") -> LotAuditEntry:
    return _recall_entry(lot_id, "recall", reason, role)
