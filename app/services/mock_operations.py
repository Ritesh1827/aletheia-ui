"""Mock operations service: overview + incidents. Demo fixtures only."""

from __future__ import annotations

from app.models.operations import (
    ActionLogEntry,
    AnchorHealth,
    ConflictingPair,
    CustodyEvent,
    IncidentDetail,
    IncidentSummary,
    IntegrityCheck,
    InvestigationAction,
    LotStatus,
    OverviewData,
    TowerMetric,
)
from app.models.verify import EvidenceFinding, ProvenanceEvent
from app.services import mock_verify


class UnknownIncidentError(Exception):
    def __init__(self, incident_id: str) -> None:
        super().__init__(f"Unknown incident: {incident_id}")
        self.incident_id = incident_id


class MockOperationsError(Exception):
    def __init__(self, correlation_id: str) -> None:
        super().__init__("Simulated operations backend failure")
        self.correlation_id = correlation_id


def _clone_findings() -> list[EvidenceFinding]:
    return mock_verify.verify_serial("AL-DEMO-0002").findings


def _clone_timeline() -> list[ProvenanceEvent]:
    return mock_verify.verify_serial("AL-DEMO-0002").timeline


def incident_summaries() -> list[IncidentSummary]:
    return [
        IncidentSummary(
            id="INC-1042",
            severity="critical",
            status="open",
            serial="AL-DEMO-0002",
            rule_id="R-VELOCITY-04",
            summary="Impossible movement — Oslo and Gdansk scans 41 minutes apart.",
            detected_at="2026-10-01 10:05 UTC",
        ),
        IncidentSummary(
            id="INC-1041",
            severity="critical",
            status="investigating",
            serial="AL-DEMO-0002",
            rule_id="R-DUP-IDENTITY-02",
            summary="Duplicate custody claims for one serial after evt-0011.",
            detected_at="2026-10-01 10:31 UTC",
        ),
        IncidentSummary(
            id="INC-1038",
            severity="watch",
            status="triaged",
            serial="AL-DEMO-0007",
            rule_id="R-ACTOR-01",
            summary="Observation from unregistered scanner held for review.",
            detected_at="2026-09-29 15:44 UTC",
        ),
        IncidentSummary(
            id="INC-1031",
            severity="info",
            status="resolved",
            serial="AL-DEMO-0001",
            rule_id="R-POST-SALE-01",
            summary="No post-sale scan yet; routine watch closed with note kept.",
            detected_at="2026-09-20 09:02 UTC",
        ),
    ]


def get_overview(
    severity: str = "all",
    status: str = "all",
    fail: bool = False,
) -> OverviewData:
    if fail:
        raise MockOperationsError(correlation_id="demo-corr-9b21")
    incidents = incident_summaries()
    if severity != "all":
        incidents = [i for i in incidents if i.severity == severity]
    if status != "all":
        incidents = [i for i in incidents if i.status == status]
    open_critical = [i for i in incident_summaries() if i.severity == "critical" and i.status != "resolved"]
    return OverviewData(
        metrics=[
            TowerMetric(id="critical", label="Open critical incidents", value=str(len(open_critical)),
                        context="2 linked to AL-DEMO-0002", tone="critical",
                        link="/incidents?severity=critical&status=open"),
            TowerMetric(id="contested", label="Contested serials", value="1",
                        context="AL-DEMO-0002 under review", tone="watch",
                        link="/incidents?status=investigating"),
            TowerMetric(id="frozen", label="Frozen lots", value="0",
                        context="No lot frozen in demo set", tone="good",
                        link="/overview?status=open#lots"),
            TowerMetric(id="anchored", label="Anchored batches", value="2",
                        context="ANCH-DEMO-1 · ANCH-DEMO-2", tone="neutral",
                        link="/overview#anchors"),
            TowerMetric(id="integrity", label="Integrity status", value="PASS",
                        context="6,214 records · 0 broken links", tone="good",
                        link="/overview#integrity"),
        ],
        incidents=incidents,
        custody_events=[
            CustodyEvent(event_id="evt-0014", timestamp="2026-10-01 10:20 UTC",
                         actor="Unknown claimant", serial="AL-DEMO-0002",
                         summary="Second custody claim submitted."),
            CustodyEvent(event_id="evt-0011", timestamp="2026-09-28 13:05 UTC",
                         actor="Harbor Retail DC → Store 14", serial="AL-DEMO-0002",
                         summary="Dispatched to retail store."),
            CustodyEvent(event_id="evt-0006", timestamp="2026-09-02 11:58 UTC",
                         actor="Northwind → Harbor Retail DC", serial="AL-DEMO-0001",
                         summary="Outbound transfer accepted."),
            CustodyEvent(event_id="evt-0005", timestamp="2026-08-26 17:25 UTC",
                         actor="Northwind Logistics", serial="AL-DEMO-0001",
                         summary="Received at regional depot."),
        ],
        anchor_health=AnchorHealth(
            latest_anchor="ANCH-DEMO-2",
            latest_block=1845517,
            successful_anchors=2,
            pending_batches=1,
            last_failure="None in demo window",
        ),
        lots=[
            LotStatus(lot_id="LOT-DEMO-A", committed_qty=10000,
                      freeze_state="Not frozen", anchor_state="Anchored · ANCH-DEMO-2"),
            LotStatus(lot_id="LOT-DEMO-B", committed_qty=2500,
                      freeze_state="Not frozen", anchor_state="Pending batch of 488"),
        ],
        integrity=[
            IntegrityCheck(name="Signature validity", status="PASS",
                           detail="6,214 / 6,214 signatures valid.", checked_at="2026-10-12 08:00 UTC"),
            IntegrityCheck(name="Chain links", status="PASS",
                           detail="0 broken links across 11 events.", checked_at="2026-10-12 08:00 UTC"),
            IntegrityCheck(name="Root matches", status="NOT CHECKED",
                           detail="On-chain root comparison runs in the anchor job, not this demo.",
                           checked_at="—"),
        ],
        updated_at="2026-10-12 09:20 UTC",
    )


def get_incident(incident_id: str) -> IncidentDetail:
    key = incident_id.strip().upper()
    if key == "INC-ERR":
        raise MockOperationsError(correlation_id="demo-corr-51ac")
    if key == "INC-1042":
        return IncidentDetail(
            id="INC-1042",
            severity="critical",
            status="open",
            serial="AL-DEMO-0002",
            detected_at="2026-10-01 10:05 UTC",
            explanation="Two scans claim serial AL-DEMO-0002 in Oslo and Gdansk, 41 minutes apart. "
            "One unit cannot plausibly cover 1,140 km in that window, so at least one scan — "
            "likely the Gdansk one from an unregistered scanner — is suspect.",
            findings=_clone_findings(),
            conflict=ConflictingPair(
                left_label="Observation A · evt-0012 · trusted",
                left_detail="Store 14 POS, Oslo · 2026-10-01 09:12 UTC · shelf scan on registered terminal.",
                right_label="Observation B · evt-0013 · suspect",
                right_detail="Unregistered scanner, Gdansk Kiosk 9 · 2026-10-01 09:53 UTC · no custody chain behind it.",
            ),
            timeline=_clone_timeline(),
            risk_score=92,
            confidence="High — detector fired on synchronized clock window of ±2 minutes.",
            uncertainty="If either scanner clock drifted beyond 2 minutes, the velocity math weakens.",
            next_steps=[
                "Quarantine the physical unit and photograph the seal and QR.",
                "Pull both scanner logs and compare device fingerprints.",
                "Keep outbound transfer frozen until the conflict resolves.",
            ],
            actions=[
                InvestigationAction(id="note", label="Add note", kind="note",
                                    detail="Notes stay attached to the case file."),
                InvestigationAction(id="accept", label="Accept and watch", kind="status",
                                    detail="Moves case to Investigating. Original findings are preserved."),
                InvestigationAction(id="export", label="Export case JSON", kind="export",
                                    detail="Downloads the demo case file."),
            ],
            action_log=[
                ActionLogEntry(at="2026-10-01 10:05 UTC", actor="detector", action="Case opened by R-VELOCITY-04."),
                ActionLogEntry(at="2026-10-01 10:31 UTC", actor="demo.verifier", action="Linked INC-1041 as duplicate-identity companion."),
            ],
        )
    if key == "INC-1041":
        detail = get_incident("INC-1042")
        detail.id = "INC-1041"
        detail.status = "investigating"
        detail.explanation = (
            "Companion case to INC-1042: after the conflicting scans, a second custody claim "
            "(evt-0014) was submitted for AL-DEMO-0002 by an unknown claimant. Outbound transfer "
            "is held until one claim is withdrawn or proven."
        )
        detail.detected_at = "2026-10-01 10:31 UTC"
        return detail
    if key == "INC-1038":
        return IncidentDetail(
            id="INC-1038",
            severity="watch",
            status="triaged",
            serial="AL-DEMO-0007",
            detected_at="2026-09-29 15:44 UTC",
            explanation="A single observation for AL-DEMO-0007 arrived from a scanner that is not "
            "in the actor registry. No conflicting custody exists yet, so this stays a watch — "
            "held for registrar review rather than quarantine.",
            findings=[
                EvidenceFinding(
                    rule_id="R-ACTOR-01",
                    severity="watch",
                    reason="Observation submitted by unregistered scanner device.",
                    references=["evt-0031"],
                    uncertainty="Device may be newly deployed and not yet registered.",
                    next_step="Registrar confirms device identity, then clears or escalates.",
                ),
            ],
            conflict=None,
            timeline=[],
            risk_score=34,
            confidence="Medium — single uncorroborated signal.",
            uncertainty="No custody context yet for AL-DEMO-0007 in this demo set.",
            next_steps=["Registrar reviews the device enrollment request."],
            actions=[
                InvestigationAction(id="note", label="Add note", kind="note"),
                InvestigationAction(id="export", label="Export case JSON", kind="export"),
            ],
            action_log=[
                ActionLogEntry(at="2026-09-29 15:44 UTC", actor="detector", action="Case opened by R-ACTOR-01."),
            ],
        )
    if key == "INC-1031":
        return IncidentDetail(
            id="INC-1031",
            severity="info",
            status="resolved",
            serial="AL-DEMO-0001",
            detected_at="2026-09-20 09:02 UTC",
            explanation="Routine watch: AL-DEMO-0001 had no post-sale scan while still in distribution "
            "custody. Expected behavior — closed with the note preserved below.",
            findings=[],
            conflict=None,
            timeline=[],
            risk_score=5,
            confidence="High — absence matches custody state.",
            uncertainty="None material.",
            next_steps=["Re-open automatically if a post-sale scan lands out of sequence."],
            actions=[
                InvestigationAction(id="export", label="Export case JSON", kind="export"),
            ],
            action_log=[
                ActionLogEntry(at="2026-09-20 09:02 UTC", actor="detector", action="Case opened by R-POST-SALE-01."),
                ActionLogEntry(at="2026-09-21 08:15 UTC", actor="demo.verifier", action="Resolved as expected behavior; findings preserved."),
            ],
        )
    raise UnknownIncidentError(incident_id=incident_id.strip())


def record_action(incident_id: str, action_id: str, note: str = "") -> ActionLogEntry:
    detail = get_incident(incident_id)
    known = {a.id for a in detail.actions}
    if action_id not in known:
        raise UnknownIncidentError(incident_id=incident_id.strip())
    text = note.strip() or {"note": "Note added.", "accept": "Case accepted for investigation.",
                            "export": "Case exported."}.get(action_id, "Action recorded.")
    return ActionLogEntry(at="2026-10-12 09:40 UTC", actor="demo.verifier",
                          action=f"{text} (demo action — no backend write)")
