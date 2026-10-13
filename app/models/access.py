"""Pydantic models for Access Control (demo session)."""

from __future__ import annotations

from pydantic import BaseModel, Field

PERMISSIONS = (
    "verify:public",
    "evidence:internal",
    "incident:annotate",
    "lot:freeze",
    "lot:recall",
    "actor:revoke",
    "redteam:run",
    "integrity:view",
)

PERMISSION_DESCRIPTIONS: dict[str, str] = {
    "verify:public": "Verify a serial and view the public verdict.",
    "evidence:internal": "View internal evidence, findings, and provenance detail.",
    "incident:annotate": "Add notes and accept cases on incidents.",
    "lot:freeze": "Freeze a lot to hold outbound transfer.",
    "lot:recall": "Recall a lot and queue pull-stock response.",
    "actor:revoke": "Revoke a registered actor.",
    "redteam:run": "Execute Red-Team Lab scenarios in the demo environment.",
    "integrity:view": "View integrity and audit summaries.",
}

ROLE_IDS = ("verifier", "operator", "investigator", "admin")


class RoleDetail(BaseModel):
    id: str
    name: str
    purpose: str
    permissions: list[str] = Field(default_factory=list)


class DemoUser(BaseModel):
    id: str
    name: str
    role_id: str
    organization: str
    status: str = "active"


class AccessAuditEntry(BaseModel):
    at: str
    actor: str
    action: str
    target: str
    outcome: str
    request_id: str = ""


class AccessOverview(BaseModel):
    current_role: RoleDetail
    current_user: DemoUser
    roles: list[RoleDetail]
    users: list[DemoUser]
    permissions: list[str]
    matrix: dict[str, dict[str, bool]]
    audit: list[AccessAuditEntry]
    is_demo: bool = True
