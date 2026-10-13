"""Pydantic models for Lots & Recall."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FreezeState = Literal["active", "frozen"]
RecallState = Literal["none", "recalled"]


class LotProduct(BaseModel):
    serial: str
    status: str
    custodian: str = ""
    sale_state: Literal["unsold", "sold", "unknown"] = "unknown"


class LotIncidentRef(BaseModel):
    id: str
    severity: str
    summary: str


class LotAnchorRef(BaseModel):
    anchor_id: str
    block: int | None = None
    tx_hash: str | None = None
    root: str = ""
    event_count: int = 0
    state: Literal["anchored", "pending"] = "anchored"


class LotAuditEntry(BaseModel):
    at: str
    actor: str
    action: str
    outcome: str
    reason: str = ""


class LotDetail(BaseModel):
    lot_id: str
    product: str
    committed_qty: int
    lifecycle: str
    freeze_state: FreezeState = "active"
    recall_state: RecallState = "none"
    permitted_custodians: list[str] = Field(default_factory=list)
    products: list[LotProduct] = Field(default_factory=list)
    incidents: list[LotIncidentRef] = Field(default_factory=list)
    anchors: list[LotAnchorRef] = Field(default_factory=list)
    audit: list[LotAuditEntry] = Field(default_factory=list)
    updated_at: str = ""


class LotSummary(BaseModel):
    lot_id: str
    product: str
    committed_qty: int
    freeze_state: FreezeState = "active"
    recall_state: RecallState = "none"
    anchor_state: str = ""
    incidents_open: int = 0


class BlastNode(BaseModel):
    label: str
    detail: str = ""
    link: str = ""
    tone: Literal["critical", "watch", "good", "neutral"] = "neutral"
    children: list[BlastNode] = Field(default_factory=list)


class BlastRadius(BaseModel):
    lot_id: str
    affected: int
    sold: int
    unsold: int
    unlocated: int
    completeness: Literal["complete", "partial", "unknown"]
    completeness_note: str = ""
    tree: list[BlastNode] = Field(default_factory=list)
    incident_links: list[str] = Field(default_factory=list)
