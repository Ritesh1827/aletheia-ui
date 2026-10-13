"""Pydantic models for Audit & Integrity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    seq: int
    event_id: str
    at: str
    actor: str
    action: str
    target: str = ""
    outcome: str = "allowed"
    context: dict[str, str] = Field(default_factory=dict)
    prev_hash: str = ""
    record_hash: str = ""


class IntegrityFailure(BaseModel):
    seq: int
    event_id: str
    reason: str
    expected: str = ""
    actual: str = ""


class IntegrityReport(BaseModel):
    status: str
    checked: int = 0
    failures: list[IntegrityFailure] = Field(default_factory=list)
    verified_at: str = ""
    note: str = ""
