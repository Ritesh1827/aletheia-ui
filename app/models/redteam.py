"""Pydantic models for the Red-Team Lab."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.verify import EvidenceFinding

ScenarioId = Literal[
    "clone-qr",
    "revoked-actor",
    "fake-handover",
    "tampered-history",
    "double-claim",
    "post-sale-scan",
]

ScenarioOutcome = Literal["detected", "rejected", "flagged", "clean", "error"]


class ScenarioField(BaseModel):
    name: str
    label: str
    placeholder: str = ""
    default: str = ""
    required: bool = True


class ScenarioMeta(BaseModel):
    id: str
    name: str
    objective: str
    detector: str
    severity: Literal["critical", "watch", "info"]
    has_run: bool = False


class FeedEntry(BaseModel):
    at: str
    kind: Literal["observation", "check", "finding"]
    text: str


class ScenarioResult(BaseModel):
    scenario_id: str
    outcome: ScenarioOutcome
    severity: Literal["critical", "watch", "info"]
    summary: str
    triggered_rules: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    serial: str = ""
    at: str = ""
    next_steps: list[str] = Field(default_factory=list)
    findings: list[EvidenceFinding] = Field(default_factory=list)
    feed: list[FeedEntry] = Field(default_factory=list)
    verify_link: str = ""
    incident_link: str = ""
    explorer_link: str = ""
    computed: str = ""
    expected: str = ""


class RedTeamLab(BaseModel):
    scenarios: list[ScenarioMeta]
    fields: dict[str, list[ScenarioField]] = Field(default_factory=dict)
