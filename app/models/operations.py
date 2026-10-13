"""Pydantic models for Control Tower and Incident Investigation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.verify import EvidenceFinding, ProvenanceEvent

IncidentSeverity = Literal["critical", "watch", "info"]
IncidentStatus = Literal["open", "triaged", "investigating", "resolved"]


class TowerMetric(BaseModel):
    id: str
    label: str
    value: str
    context: str
    tone: Literal["critical", "watch", "good", "neutral"] = "neutral"
    link: str


class IncidentSummary(BaseModel):
    id: str
    severity: IncidentSeverity
    status: IncidentStatus
    serial: str
    rule_id: str
    summary: str
    detected_at: str


class ConflictingPair(BaseModel):
    left_label: str
    left_detail: str
    right_label: str
    right_detail: str


class CustodyEvent(BaseModel):
    event_id: str
    timestamp: str
    actor: str
    summary: str
    serial: str = ""


class AnchorHealth(BaseModel):
    latest_anchor: str
    latest_block: int
    successful_anchors: int
    pending_batches: int
    last_failure: str


class LotStatus(BaseModel):
    lot_id: str
    committed_qty: int
    freeze_state: str
    anchor_state: str


class IntegrityCheck(BaseModel):
    name: str
    status: Literal["PASS", "FAIL", "NOT CHECKED", "STALE"]
    detail: str
    checked_at: str


class OverviewData(BaseModel):
    metrics: list[TowerMetric]
    incidents: list[IncidentSummary]
    custody_events: list[CustodyEvent]
    anchor_health: AnchorHealth
    lots: list[LotStatus]
    integrity: list[IntegrityCheck]
    updated_at: str


class InvestigationAction(BaseModel):
    id: str
    label: str
    kind: Literal["note", "status", "export"] = "note"
    detail: str = ""


class ActionLogEntry(BaseModel):
    at: str
    actor: str
    action: str


class IncidentDetail(BaseModel):
    id: str
    severity: IncidentSeverity
    status: IncidentStatus
    serial: str
    detected_at: str
    explanation: str
    findings: list[EvidenceFinding] = Field(default_factory=list)
    conflict: ConflictingPair | None = None
    timeline: list[ProvenanceEvent] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)
    confidence: str = ""
    uncertainty: str = ""
    next_steps: list[str] = Field(default_factory=list)
    actions: list[InvestigationAction] = Field(default_factory=list)
    action_log: list[ActionLogEntry] = Field(default_factory=list)
