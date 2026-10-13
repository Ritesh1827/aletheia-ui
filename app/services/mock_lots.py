"""Mock lots service. Deterministic demo inventory, blast radius, freeze/recall.

State (frozen / recalled / audit) lives in module-level demo stores so the
workflow can be exercised end to end. Nothing here touches real inventory,
contracts, or partners — every mutation is labelled a demo operation.
"""

from __future__ import annotations

from app.models.lots import (
    BlastNode,
    BlastRadius,
    LotAnchorRef,
    LotAuditEntry,
    LotDetail,
    LotIncidentRef,
    LotProduct,
    LotSummary,
)
from app.services import mock_explorer

_DEMO_AT = "2026-10-12T11:00:00Z"

_FROZEN: dict[str, bool] = {}
_RECALLED: dict[str, bool] = {}
_AUDIT: dict[str, list[LotAuditEntry]] = {}


class UnknownLotError(Exception):
    def __init__(self, lot_id: str) -> None:
        super().__init__(f"Unknown lot: {lot_id}")
        self.lot_id = lot_id


class LotsBackendError(Exception):
    def __init__(self, correlation_id: str) -> None:
        super().__init__("Simulated lots backend failure")
        self.correlation_id = correlation_id


def _audit(lot_id: str) -> list[LotAuditEntry]:
    return _AUDIT.setdefault(lot_id, [])


def _frozen(lot_id: str) -> bool:
    return _FROZEN.get(lot_id.upper(), False)


def _recalled(lot_id: str) -> bool:
    return _RECALLED.get(lot_id.upper(), False)


def lot_ids() -> list[str]:
    return ["LOT-DEMO-A", "LOT-DEMO-B"]


def list_lots(query: str = "", freeze: str = "all", fail: bool = False) -> list[LotSummary]:
    if fail:
        raise LotsBackendError(correlation_id="demo-corr-31fa")
    lots = [
        LotSummary(
            lot_id="LOT-DEMO-A", product="Oxide Sensor Housing · Rev C",
            committed_qty=10000,
            freeze_state="frozen" if _frozen("LOT-DEMO-A") else "active",
            recall_state="recalled" if _recalled("LOT-DEMO-A") else "none",
            anchor_state="Anchored · ANCH-DEMO-2", incidents_open=2,
        ),
        LotSummary(
            lot_id="LOT-DEMO-B", product="Oxide Sensor Housing · Rev C",
            committed_qty=2500,
            freeze_state="frozen" if _frozen("LOT-DEMO-B") else "active",
            recall_state="recalled" if _recalled("LOT-DEMO-B") else "none",
            anchor_state="Pending · BATCH-PENDING-3", incidents_open=0,
        ),
    ]
    q = query.strip().lower()
    if q:
        lots = [l for l in lots if q in l.lot_id.lower() or q in l.product.lower()]
    if freeze == "frozen":
        lots = [l for l in lots if l.freeze_state == "frozen"]
    elif freeze == "active":
        lots = [l for l in lots if l.freeze_state == "active"]
    return lots


def get_lot(lot_id: str) -> LotDetail:
    key = lot_id.strip().upper()
    if key == "LOT-ERR":
        raise LotsBackendError(correlation_id="demo-corr-88c2")
    if key == "LOT-DEMO-A":
        anchors = [
            LotAnchorRef(anchor_id="ANCH-DEMO-2", block=mock_explorer.BLOCK_B,
                         tx_hash=mock_explorer.TX_B, root=mock_explorer.ROOT_B,
                         event_count=488, state="anchored"),
            LotAnchorRef(anchor_id="ANCH-DEMO-1", block=mock_explorer.BLOCK_A,
                         tx_hash=mock_explorer.TX_A, root=mock_explorer.ROOT_A,
                         event_count=512, state="anchored"),
        ]
        return LotDetail(
            lot_id="LOT-DEMO-A", product="Oxide Sensor Housing · Rev C",
            committed_qty=10000, lifecycle="In distribution",
            freeze_state="frozen" if _frozen(key) else "active",
            recall_state="recalled" if _recalled(key) else "none",
            permitted_custodians=["Acme Manufacturing", "Northwind Logistics",
                                  "Harbor Retail DC"],
            products=[
                LotProduct(serial="AL-DEMO-0001", status="In distribution",
                           custodian="Northwind → Harbor Retail DC", sale_state="unsold"),
                LotProduct(serial="AL-DEMO-0002", status="Contested",
                           custodian="Harbor Retail DC → Store 14", sale_state="unknown"),
            ],
            incidents=[
                LotIncidentRef(id="INC-1042", severity="critical",
                               summary="Impossible movement — Oslo and Gdansk scans 41 minutes apart."),
                LotIncidentRef(id="INC-1041", severity="critical",
                               summary="Duplicate custody claims for one serial after evt-0011."),
            ],
            anchors=anchors, audit=list(_audit(key)),
            updated_at="2026-10-12 09:20 UTC",
        )
    if key == "LOT-DEMO-B":
        return LotDetail(
            lot_id="LOT-DEMO-B", product="Oxide Sensor Housing · Rev C",
            committed_qty=2500, lifecycle="Awaiting first anchor",
            freeze_state="frozen" if _frozen(key) else "active",
            recall_state="recalled" if _recalled(key) else "none",
            permitted_custodians=["Acme Manufacturing"],
            products=[],
            incidents=[],
            anchors=[
                LotAnchorRef(anchor_id="BATCH-PENDING-3", block=None, tx_hash=None,
                             root="", event_count=96, state="pending"),
            ],
            audit=list(_audit(key)),
            updated_at="2026-10-12 09:20 UTC",
        )
    raise UnknownLotError(lot_id=lot_id.strip())


def get_blast_radius(lot_id: str) -> BlastRadius:
    key = lot_id.strip().upper()
    if key == "LOT-ERR":
        raise LotsBackendError(correlation_id="demo-corr-88c2")
    if key == "LOT-DEMO-A":
        return BlastRadius(
            lot_id="LOT-DEMO-A",
            affected=2, sold=0, unsold=1, unlocated=1,
            completeness="partial",
            completeness_note="Only 2 of 10,000 committed units have observed demo records. "
                              "Counts below cover observed units only — the remainder of the lot "
                              "is unlocated in this demo, not confirmed safe.",
            tree=[
                BlastNode(
                    label="LOT-DEMO-A · 10,000 committed",
                    detail="Anchored · ANCH-DEMO-2", tone="neutral",
                    children=[
                        BlastNode(
                            label="AL-DEMO-0001 · unsold",
                            detail="Northwind → Harbor Retail DC · in distribution",
                            link="/verify/AL-DEMO-0001", tone="good",
                        ),
                        BlastNode(
                            label="AL-DEMO-0002 · status unknown",
                            detail="Contested · conflicting Oslo/Gdansk observations",
                            link="/verify/AL-DEMO-0002", tone="critical",
                            children=[
                                BlastNode(label="INC-1042 · velocity conflict",
                                          detail="Impossible movement, 41 min apart",
                                          link="/incidents/INC-1042", tone="critical"),
                                BlastNode(label="INC-1041 · duplicate claims",
                                          detail="Second custody claim evt-0014",
                                          link="/incidents/INC-1041", tone="critical"),
                            ],
                        ),
                        BlastNode(
                            label="9,998 unobserved units · unlocated in demo",
                            detail="No demo scans or custody events recorded — unknown, not safe",
                            tone="watch",
                        ),
                    ],
                ),
            ],
            incident_links=["INC-1042", "INC-1041"],
        )
    if key == "LOT-DEMO-B":
        return BlastRadius(
            lot_id="LOT-DEMO-B",
            affected=0, sold=0, unsold=0, unlocated=0,
            completeness="unknown",
            completeness_note="No product-level demo records exist for this lot yet — "
                              "its batch is still pending anchor. Nothing to trace.",
            tree=[],
            incident_links=[],
        )
    raise UnknownLotError(lot_id=lot_id.strip())


def freeze_lot(lot_id: str, reason: str = "", actor: str = "demo.verifier") -> LotAuditEntry:
    detail = get_lot(lot_id)
    key = detail.lot_id
    if _frozen(key):
        entry = LotAuditEntry(at=_DEMO_AT, actor=actor,
                              action=f"Freeze {key} re-confirmed",
                              outcome="already-frozen — no state change",
                              reason=reason.strip() or "Repeat confirmation; idempotent.")
        _audit(key).append(entry)
        return entry
    _FROZEN[key] = True
    entry = LotAuditEntry(at=_DEMO_AT, actor=actor,
                          action=f"Freeze {key}",
                          outcome="frozen — outbound transfer held (demo operation)",
                          reason=reason.strip() or "Investigator hold pending conflict review.")
    _audit(key).append(entry)
    return entry


def recall_lot(lot_id: str, reason: str = "", actor: str = "demo.recall-manager") -> LotAuditEntry:
    detail = get_lot(lot_id)
    key = detail.lot_id
    if _recalled(key):
        entry = LotAuditEntry(at=_DEMO_AT, actor=actor,
                              action=f"Recall {key} re-confirmed",
                              outcome="already-recalled — no state change",
                              reason=reason.strip() or "Repeat confirmation; idempotent.")
        _audit(key).append(entry)
        return entry
    _RECALLED[key] = True
    _FROZEN[key] = True
    entry = LotAuditEntry(at=_DEMO_AT, actor=actor,
                          action=f"Recall {key}",
                          outcome="recalled + frozen — pull-stock tasks queued (demo operation)",
                          reason=reason.strip() or "Clone conflict on AL-DEMO-0002.")
    _audit(key).append(entry)
    return entry


def reset_demo_state() -> None:
    _FROZEN.clear()
    _RECALLED.clear()
    _AUDIT.clear()
