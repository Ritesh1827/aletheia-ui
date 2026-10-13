"""Mock verification service. All data labelled DEMO DATA in UI."""

from __future__ import annotations

from app.models.verify import (
    AnchorProof,
    CheckResult,
    EvidenceFinding,
    ProductIdentity,
    ProvenanceEvent,
    VerificationVerdict,
)
from app.services.mock_explorer import ROOT_A, ROOT_B


class UnknownSerialError(Exception):
    def __init__(self, serial: str) -> None:
        super().__init__(f"Unknown serial: {serial}")
        self.serial = serial


class MockBackendError(Exception):
    def __init__(self, correlation_id: str) -> None:
        super().__init__("Simulated backend failure")
        self.correlation_id = correlation_id


def _verified() -> VerificationVerdict:
    return VerificationVerdict(
        serial="AL-DEMO-0001",
        verdict="VERIFIED",
        explanation="All available history checks are consistent for this serial. "
        "Lot commitment matches, custody sequence is ordered, and the anchor proof is present.",
        risk_score=8,
        confidence="High — 6 events observed across 3 custodians.",
        uncertainty="No post-sale observation exists yet for this unit.",
        retrieved_at="2026-10-12T09:14:00Z",
        identity=ProductIdentity(
            serial="AL-DEMO-0001",
            lot_id="LOT-DEMO-A",
            product="Oxide Sensor Housing · Rev C",
            lifecycle_status="In distribution",
            permitted_custodian="Northwind Logistics",
        ),
        checks=[
            CheckResult(id="lot", label="Lot commitment", status="pass",
                        detail="Serial is committed under LOT-DEMO-A root 9f2c…41ab."),
            CheckResult(id="chain", label="Chain integrity", status="pass",
                        detail="6 events hash-linked, no gaps detected."),
            CheckResult(id="actor", label="Actor authorization", status="pass",
                        detail="All submitting actors are registered and active."),
            CheckResult(id="custody", label="Custody sequence", status="pass",
                        detail="Offer → accept → receive ordering holds at each hop."),
            CheckResult(id="movement", label="Movement plausibility", status="pass",
                        detail="Distances and dwell times within expected corridors."),
        ],
        findings=[
            EvidenceFinding(
                rule_id="R-POST-SALE-01",
                severity="info",
                reason="No post-sale scan recorded; unit still inside distribution custody.",
                references=["evt-0006"],
                uncertainty="Absence of a scan is not evidence of absence of sale.",
                next_step="Re-verify after retailer receive event lands.",
            ),
        ],
        timeline=[
            ProvenanceEvent(event_id="evt-0001", timestamp="2026-08-04 08:12 UTC",
                            kind="custody", actor="Acme Manufacturing",
                            summary="Manufactured and commissioned.", location="Plant 2 · Line B"),
            ProvenanceEvent(event_id="evt-0002", timestamp="2026-08-04 08:13 UTC",
                            kind="observation", actor="Acme QA",
                            summary="Quality gate passed; seal-ID bound.", location="Plant 2 · QA"),
            ProvenanceEvent(event_id="evt-0003", timestamp="2026-08-11 14:40 UTC",
                            kind="custody", actor="Acme Manufacturing → Northwind",
                            summary="Custody offered and accepted.", location="Hub KPH-1"),
            ProvenanceEvent(event_id="evt-0004", timestamp="2026-08-19 09:02 UTC",
                            kind="observation", actor="Northwind Scanner 7",
                            summary="In-transit observation ping.", location="Corridor KPH → OSL"),
            ProvenanceEvent(event_id="evt-0005", timestamp="2026-08-26 17:25 UTC",
                            kind="custody", actor="Northwind Logistics",
                            summary="Received at regional depot.", location="Depot OSL-3"),
            ProvenanceEvent(event_id="evt-0006", timestamp="2026-09-02 11:58 UTC",
                            kind="custody", actor="Northwind → Harbor Retail DC",
                            summary="Outbound transfer accepted.", location="Depot OSL-3"),
        ],
        proof=AnchorProof(
            anchor_id="ANCH-DEMO-1",
            merkle_root=ROOT_A,
            transaction_hash="0x7a3f9c1e5b2846d0a9c4e71f3b8d2a6c5e0f1a2b",
            block_height=1841204,
            proof_status="NOT VERIFIED",
            leaf_count=512,
        ),
    )


def _clone() -> VerificationVerdict:
    return VerificationVerdict(
        serial="AL-DEMO-0002",
        verdict="CLONE_DETECTED",
        explanation="Two histories claim this serial in different places at overlapping times. "
        "Treat the physical item as suspect until an investigator resolves the conflict.",
        risk_score=92,
        confidence="High — conflicting observations 41 minutes apart across regions.",
        uncertainty="One of the two observation sets may come from a cloned QR.",
        retrieved_at="2026-10-12T09:16:00Z",
        identity=ProductIdentity(
            serial="AL-DEMO-0002",
            lot_id="LOT-DEMO-A",
            product="Oxide Sensor Housing · Rev C",
            lifecycle_status="Contested",
            permitted_custodian="Harbor Retail DC",
        ),
        checks=[
            CheckResult(id="lot", label="Lot commitment", status="pass",
                        detail="Serial is committed under LOT-DEMO-A."),
            CheckResult(id="chain", label="Chain integrity", status="pass",
                        detail="Off-chain log links verify; conflict is in observations, not hashes."),
            CheckResult(id="actor", label="Actor authorization", status="warn",
                        detail="One observation submitted by an unregistered scanner."),
            CheckResult(id="custody", label="Custody sequence", status="fail",
                        detail="Custody claims diverge after evt-0011."),
            CheckResult(id="movement", label="Movement plausibility", status="fail",
                        detail="Oslo and Gdansk observations 41 minutes apart — implausible for one unit."),
        ],
        findings=[
            EvidenceFinding(
                rule_id="R-VELOCITY-04",
                severity="critical",
                reason="Impossible movement: scans 1,140 km apart within 41 minutes.",
                references=["evt-0012", "evt-0013"],
                uncertainty="Scanner clocks assumed synchronized within 2 minutes.",
                next_step="Quarantine unit; escalate to investigator with both scans attached.",
            ),
            EvidenceFinding(
                rule_id="R-DUP-IDENTITY-02",
                severity="critical",
                reason="Duplicate identity: two active custody claims for one serial.",
                references=["evt-0011", "evt-0014"],
                next_step="Freeze outbound transfer until conflict resolved.",
            ),
        ],
        timeline=[
            ProvenanceEvent(event_id="evt-0010", timestamp="2026-09-20 10:00 UTC",
                            kind="custody", actor="Harbor Retail DC",
                            summary="Received at retail distribution center.", location="Depot OSL-3"),
            ProvenanceEvent(event_id="evt-0011", timestamp="2026-09-28 13:05 UTC",
                            kind="custody", actor="Harbor Retail DC → Store 14",
                            summary="Dispatched to retail store.", location="Oslo · Store 14"),
            ProvenanceEvent(event_id="evt-0012", timestamp="2026-10-01 09:12 UTC",
                            kind="observation", actor="Store 14 POS",
                            summary="Shelf scan in Oslo.", location="Oslo · Store 14"),
            ProvenanceEvent(event_id="evt-0013", timestamp="2026-10-01 09:53 UTC",
                            kind="observation", actor="Unregistered scanner",
                            summary="Conflicting scan in Gdansk.", location="Gdansk · Kiosk 9"),
            ProvenanceEvent(event_id="evt-0014", timestamp="2026-10-01 10:20 UTC",
                            kind="custody", actor="Unknown claimant",
                            summary="Second custody claim submitted.", location="Withheld — under review"),
        ],
        proof=AnchorProof(
            anchor_id="ANCH-DEMO-2",
            merkle_root=ROOT_B,
            transaction_hash="0x3d8b21f64a07c9e15d0f42a8c6e9b3d715c8a4",
            block_height=1845517,
            proof_status="NOT VERIFIED",
            leaf_count=488,
        ),
    )


def verify_serial(serial: str) -> VerificationVerdict:
    """Return the mock verdict for a serial. Raises typed errors, never None."""
    key = serial.strip().upper()
    if key == "AL-DEMO-ERR":
        raise MockBackendError(correlation_id="demo-corr-7f3a")
    if key == "AL-DEMO-0001":
        return _verified()
    if key == "AL-DEMO-0002":
        return _clone()
    raise UnknownSerialError(serial=serial.strip())
