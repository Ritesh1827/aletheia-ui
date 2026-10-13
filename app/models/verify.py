"""Pydantic models for Product Verify."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal[
    "VERIFIED", "SUSPICIOUS", "CLONE_DETECTED", "TAMPERED", "RECALLED", "UNKNOWN"
]

VERDICT_LABELS: dict[str, str] = {
    "VERIFIED": "History checks passed",
    "SUSPICIOUS": "History needs review",
    "CLONE_DETECTED": "Conflicting histories detected",
    "TAMPERED": "Integrity check failed",
    "RECALLED": "Lot recalled / frozen",
    "UNKNOWN": "Product identity not recognized",
}

VERDICT_CAVEAT = (
    "This verdict assesses available records and history. "
    "It does not independently prove the physical item is genuine."
)


class ProductIdentity(BaseModel):
    serial: str
    lot_id: str
    product: str
    lifecycle_status: str
    permitted_custodian: str


class CheckResult(BaseModel):
    id: str
    label: str
    status: Literal["pass", "fail", "warn", "unknown"]
    detail: str


class EvidenceFinding(BaseModel):
    rule_id: str
    severity: Literal["info", "watch", "critical"]
    reason: str
    references: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    next_step: str = ""


class ProvenanceEvent(BaseModel):
    event_id: str
    timestamp: str
    kind: Literal["custody", "observation"]
    actor: str
    summary: str
    location: str = ""


class AnchorProof(BaseModel):
    anchor_id: str
    merkle_root: str
    transaction_hash: str
    block_height: int
    proof_status: Literal["NOT VERIFIED", "PROOF VALID", "PROOF INVALID"]
    leaf_count: int


class VerificationVerdict(BaseModel):
    serial: str
    verdict: Verdict
    explanation: str
    risk_score: int = Field(ge=0, le=100)
    confidence: str
    uncertainty: str
    retrieved_at: str
    identity: ProductIdentity
    checks: list[CheckResult]
    findings: list[EvidenceFinding] = Field(default_factory=list)
    timeline: list[ProvenanceEvent] = Field(default_factory=list)
    proof: AnchorProof | None = None
