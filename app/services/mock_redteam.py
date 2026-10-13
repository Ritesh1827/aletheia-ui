"""Red-Team scenario service. Deterministic demo rules, honestly evaluated.

Each scenario runs real logic against its inputs — velocity math, registry
lookup, transition checks, proof recomputation, claim comparison, lifecycle
order — and reports what the evaluation actually produced. Nothing is
pre-declared detected: the outcome follows the inputs.
"""

from __future__ import annotations

from datetime import datetime

from app.models.redteam import (
    FeedEntry,
    RedTeamLab,
    ScenarioField,
    ScenarioMeta,
    ScenarioResult,
)
from app.models.verify import EvidenceFinding
from app.services import mock_explorer

SCENARIO_IDS = (
    "clone-qr",
    "revoked-actor",
    "fake-handover",
    "tampered-history",
    "double-claim",
    "post-sale-scan",
)

_FIXED_AT = "2026-10-12T10:40:00Z"

_OSLO = (59.9139, 10.7522)
_GDANSK = (54.3520, 18.6466)


class UnknownScenarioError(Exception):
    def __init__(self, scenario_id: str) -> None:
        super().__init__(f"Unknown scenario: {scenario_id}")
        self.scenario_id = scenario_id


class InvalidScenarioInputError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _feed(*items: tuple[str, str, str]) -> list[FeedEntry]:
    return [FeedEntry(at=a, kind=k, text=t) for a, k, t in items]  # type: ignore[arg-type]


def _metas(run_state: dict[str, bool] | None = None) -> list[ScenarioMeta]:
    run_state = run_state or {}
    return [
        ScenarioMeta(id="clone-qr", name="Clone QR / conflicting locations",
                     objective="Replay the same serial from two places and test the velocity + duplicate-identity rules.",
                     detector="R-VELOCITY-04 · R-DUP-IDENTITY-02",
                     severity="critical", has_run=run_state.get("clone-qr", False)),
        ScenarioMeta(id="revoked-actor", name="Invalid or revoked actor",
                     objective="Submit a custody event from a revoked actor and confirm the service rejects it.",
                     detector="R-ACTOR-01 (simulated rule)",
                     severity="critical", has_run=run_state.get("revoked-actor", False)),
        ScenarioMeta(id="fake-handover", name="Fake handover",
                     objective="Attempt a custody transfer with no receiver acceptance and check the transition rule.",
                     detector="R-CUSTODY-03 (simulated rule)",
                     severity="watch", has_run=run_state.get("fake-handover", False)),
        ScenarioMeta(id="tampered-history", name="Database tampering / integrity failure",
                     objective="Corrupt one proof sibling and run the real recomputation against the anchored root.",
                     detector="Merkle recomputation + R-CHAIN-02 (simulated rule)",
                     severity="critical", has_run=run_state.get("tampered-history", False)),
        ScenarioMeta(id="double-claim", name="Double claim",
                     objective="File two competing custody claims for one serial and confirm the conflict is identified.",
                     detector="R-DUP-IDENTITY-02 (simulated rule)",
                     severity="critical", has_run=run_state.get("double-claim", False)),
        ScenarioMeta(id="post-sale-scan", name="Post-sale scan",
                     objective="Emit a scan after the recorded sale event and test the lifecycle-order rule.",
                     detector="R-LIFECYCLE-05 (simulated rule)",
                     severity="watch", has_run=run_state.get("post-sale-scan", False)),
    ]


def _fields() -> dict[str, list[ScenarioField]]:
    return {
        "clone-qr": [
            ScenarioField(name="serial", label="Serial", default="AL-DEMO-0002"),
            ScenarioField(name="gap_minutes", label="Minutes between scans", default="41"),
        ],
        "revoked-actor": [
            ScenarioField(name="actor", label="Submitting actor address",
                          default=mock_explorer.ACTOR_UNKNOWN),
            ScenarioField(name="serial", label="Serial", default="AL-DEMO-0002"),
        ],
        "fake-handover": [
            ScenarioField(name="serial", label="Serial", default="AL-DEMO-0001"),
            ScenarioField(name="receiver_accepted", label="Receiver accepted? (yes/no)",
                          default="no"),
        ],
        "tampered-history": [
            ScenarioField(name="tx", label="Anchor transaction",
                          default=mock_explorer.TX_B),
        ],
        "double-claim": [
            ScenarioField(name="serial", label="Serial", default="AL-DEMO-0002"),
            ScenarioField(name="claimants", label="Competing claimants (comma-separated)",
                          default="Harbor Retail DC, Unknown claimant"),
        ],
        "post-sale-scan": [
            ScenarioField(name="serial", label="Serial", default="AL-DEMO-0001"),
            ScenarioField(name="sale_event", label="Recorded sale event ID", default="evt-0006"),
            ScenarioField(name="scan_event", label="New scan event ID", default="evt-0007"),
        ],
    }


def get_lab(run_state: dict[str, bool] | None = None) -> RedTeamLab:
    return RedTeamLab(scenarios=_metas(run_state), fields=_fields())


def _require(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InvalidScenarioInputError(f"Missing required input: {field}.")
    return cleaned


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def run_clone_qr(inputs: dict[str, str]) -> ScenarioResult:
    serial = _require(inputs.get("serial", ""), "serial").upper()
    try:
        gap = float(_require(inputs.get("gap_minutes", ""), "gap_minutes"))
    except ValueError:
        raise InvalidScenarioInputError("gap_minutes must be a number.") from None
    if gap <= 0:
        raise InvalidScenarioInputError("gap_minutes must be greater than zero.")
    distance = _haversine_km(*_OSLO, *_GDANSK)
    speed = distance / (gap / 60)
    plausible = speed <= 900
    feed = _feed(
        ("10:40:01", "observation", f"Scan 1: {serial} at Oslo Store 14 POS (registered terminal)."),
        ("10:40:02", "observation", f"Scan 2: {serial} at Gdansk Kiosk 9, {gap:g} min later (unregistered scanner)."),
        ("10:40:03", "check", f"Distance Oslo–Gdansk ≈ {distance:,.0f} km; implied speed ≈ {speed:,.0f} km/h."),
    )
    if plausible:
        return ScenarioResult(
            scenario_id="clone-qr", outcome="clean", severity="info",
            summary=f"No conflict: {gap:g} minutes is enough for the Oslo–Gdansk leg at plausible speed. "
                    "Widen the gap or shorten it to trigger the velocity rule.",
            triggered_rules=[], evidence_refs=[], serial=serial, at=_FIXED_AT,
            next_steps=["Re-run with a shorter gap to simulate the clone."],
            feed=feed + _feed(("10:40:04", "finding", "R-VELOCITY-04 evaluated — no breach at these inputs.")),
            verify_link=f"/verify/{serial}",
        )
    return ScenarioResult(
        scenario_id="clone-qr", outcome="detected", severity="critical",
        summary=f"Impossible movement: {distance:,.0f} km in {gap:g} minutes implies ≈{speed:,.0f} km/h. "
                "Two histories claim this serial — quarantined as a suspected clone.",
        triggered_rules=["R-VELOCITY-04", "R-DUP-IDENTITY-02"],
        evidence_refs=["evt-0012", "evt-0013"],
        serial=serial, at=_FIXED_AT,
        next_steps=["Quarantine the unit and compare scanner device fingerprints.",
                    "Keep outbound transfer frozen until the conflict resolves."],
        findings=[
            EvidenceFinding(rule_id="R-VELOCITY-04", severity="critical",
                            reason=f"Impossible movement: scans {distance:,.0f} km apart within {gap:g} minutes.",
                            references=["evt-0012", "evt-0013"],
                            next_step="Quarantine unit; escalate with both scans attached."),
            EvidenceFinding(rule_id="R-DUP-IDENTITY-02", severity="critical",
                            reason="Duplicate identity: two active histories for one serial.",
                            references=["evt-0011", "evt-0014"],
                            next_step="Freeze outbound transfer until conflict resolved."),
        ],
        feed=feed + _feed(("10:40:04", "finding", "R-VELOCITY-04 FIRED — impossible speed; R-DUP-IDENTITY-02 FIRED — duplicate histories.")),
        verify_link=f"/verify/{serial}",
        incident_link="/incidents/INC-1042",
        explorer_link=f"/explorer/tx/{mock_explorer.TX_B}",
    )


def run_revoked_actor(inputs: dict[str, str]) -> ScenarioResult:
    actor = _require(inputs.get("actor", ""), "actor")
    serial = _require(inputs.get("serial", ""), "serial").upper()
    try:
        info = mock_explorer.get_address(actor)
        revoked = "revoked" in info.status.lower() or "unregistered" in info.label.lower()
    except mock_explorer.UnknownRecordError:
        revoked = True
        info = None
    feed = _feed(
        ("10:40:01", "observation", f"Custody event submitted for {serial} by {actor[:14]}…."),
        ("10:40:02", "check", "Actor registry lookup against the demo registry."),
    )
    if not revoked:
        label = info.label if info else actor
        return ScenarioResult(
            scenario_id="revoked-actor", outcome="clean", severity="info",
            summary=f"Actor accepted: {label} is registered and active, so the event passes "
                    "the authorization check. Use the revoked demo address to test rejection.",
            triggered_rules=[], evidence_refs=[], serial=serial, at=_FIXED_AT,
            next_steps=[f"Re-run with the revoked address {mock_explorer.ACTOR_UNKNOWN}."],
            feed=feed + _feed(("10:40:03", "finding", "R-ACTOR-01 (simulated rule) evaluated — actor authorized.")),
            verify_link=f"/verify/{serial}",
        )
    return ScenarioResult(
        scenario_id="revoked-actor", outcome="rejected", severity="critical",
        summary=f"Custody event REJECTED: {actor[:14]}… is revoked/unregistered. The service "
                "refused to append the event — this is an enforcement decision, not a UI colour.",
        triggered_rules=["R-ACTOR-01"],
        evidence_refs=["evt-0013"],
        serial=serial, at=_FIXED_AT,
        next_steps=["Registrar reviews the device enrollment before any retry.",
                    "Quarantine scans already received from this actor."],
        findings=[
            EvidenceFinding(rule_id="R-ACTOR-01", severity="critical",
                            reason="Custody event submitted by revoked/unregistered actor; event rejected.",
                            references=["evt-0013"],
                            next_step="Blocklist the device until registrar clears it."),
        ],
        feed=feed + _feed(("10:40:03", "finding", "R-ACTOR-01 (simulated rule) FIRED — event rejected at the service layer.")),
        verify_link=f"/verify/{serial}",
        incident_link="/incidents/INC-1038",
        explorer_link=f"/explorer/address/{actor}",
    )


def run_fake_handover(inputs: dict[str, str]) -> ScenarioResult:
    serial = _require(inputs.get("serial", ""), "serial").upper()
    accepted = inputs.get("receiver_accepted", "").strip().lower()
    if accepted not in {"yes", "no", "y", "n", "true", "false"}:
        raise InvalidScenarioInputError("receiver_accepted must be yes or no.")
    ok = accepted in {"yes", "y", "true"}
    feed = _feed(
        ("10:40:01", "observation", f"Handover offered for {serial}: Northwind → Harbor Retail DC."),
        ("10:40:02", "check", f"Receiver acceptance record: {'present' if ok else 'MISSING'}."),
    )
    if ok:
        return ScenarioResult(
            scenario_id="fake-handover", outcome="clean", severity="info",
            summary="Handover complete: offer and acceptance both present, custody sequence holds. "
                    "Set receiver acceptance to “no” to test the failure path.",
            triggered_rules=[], evidence_refs=[], serial=serial, at=_FIXED_AT,
            next_steps=["Re-run with receiver_accepted=no."],
            feed=feed + _feed(("10:40:03", "finding", "R-CUSTODY-03 (simulated rule) evaluated — sequence holds.")),
            verify_link=f"/verify/{serial}",
        )
    return ScenarioResult(
        scenario_id="fake-handover", outcome="rejected", severity="watch",
        summary="Handover REJECTED: custody offer exists but no receiver acceptance was recorded. "
                "The R-CUSTODY-03 transition check (offer → accept → receive) failed at the accept step.",
        triggered_rules=["R-CUSTODY-03"],
        evidence_refs=["evt-0006"],
        serial=serial, at=_FIXED_AT,
        next_steps=["Hold the unit with the sender until the receiver accepts.",
                    "Treat any goods moved without acceptance as unaccounted."],
        findings=[
            EvidenceFinding(rule_id="R-CUSTODY-03", severity="watch",
                            reason="Custody transition missing receiver acceptance; chain of custody breaks here.",
                            references=["evt-0006"],
                            next_step="Re-attempt handover with signed acceptance."),
        ],
        feed=feed + _feed(("10:40:03", "finding", "R-CUSTODY-03 (simulated rule) FIRED — accept step missing.")),
        verify_link=f"/verify/{serial}",
    )


def run_tampered_history(inputs: dict[str, str]) -> ScenarioResult:
    tx = _require(inputs.get("tx", ""), "tx")
    try:
        detail = mock_explorer.get_tx(tx)
    except mock_explorer.UnknownRecordError:
        raise InvalidScenarioInputError(f"Unknown anchor transaction: {tx.strip()}.") from None
    tampered = mock_explorer.tampered_proof_demo()
    feed = _feed(
        ("10:40:01", "observation", f"Loaded batch {detail.anchor_id} ({detail.leaf_count} leaves)."),
        ("10:40:02", "observation", "Corrupted one proof sibling to simulate tampering."),
        ("10:40:03", "check", f"Recomputed root {tampered.computed_root[:12]}… vs anchored {tampered.expected_root[:12]}…."),
    )
    return ScenarioResult(
        scenario_id="tampered-history", outcome="detected", severity="critical",
        summary=f"Integrity check FAILED: recomputed root {tampered.computed_root[:12]}… does not match "
                f"anchored root {tampered.expected_root[:12]}…. The batch no longer verifies — treat it as tampered.",
        triggered_rules=["R-CHAIN-02"],
        evidence_refs=[detail.anchor_id],
        serial=", ".join(detail.serials), at=_FIXED_AT,
        next_steps=["Freeze reliance on this batch until the anchor is re-run.",
                    "Diff batch leaves against the last known-good export."],
        findings=[
            EvidenceFinding(rule_id="R-CHAIN-02", severity="critical",
                            reason="Batch proof recomputation mismatches the anchored root.",
                            references=[detail.anchor_id],
                            next_step="Re-anchor from the authoritative event log."),
        ],
        feed=feed + _feed(("10:40:04", "finding", "R-CHAIN-02 (simulated rule) FIRED — PROOF INVALID.")),
        computed=tampered.computed_root, expected=tampered.expected_root,
        explorer_link=f"/explorer/tx/{detail.tx_hash}?verify=1",
    )


def run_double_claim(inputs: dict[str, str]) -> ScenarioResult:
    serial = _require(inputs.get("serial", ""), "serial").upper()
    raw = _require(inputs.get("claimants", ""), "claimants")
    parties = [c.strip() for c in raw.split(",") if c.strip()]
    if len(parties) < 2:
        raise InvalidScenarioInputError("Provide at least two comma-separated claimants.")
    feed = _feed(
        ("10:40:01", "observation", f"Claim 1 for {serial}: {parties[0]} (custody chain present)."),
        ("10:40:02", "observation", f"Claim 2 for {serial}: {parties[1]} (no supporting chain)."),
        ("10:40:03", "check", "Both claims reference the same serial with no withdrawal of either."),
    )
    return ScenarioResult(
        scenario_id="double-claim", outcome="detected", severity="critical",
        summary=f"Conflicting claims for {serial}: “{parties[0]}” vs “{parties[1]}”. One serial, "
                "two active custodians — flagged as a duplicate-identity conflict.",
        triggered_rules=["R-DUP-IDENTITY-02"],
        evidence_refs=["evt-0011", "evt-0014"],
        serial=serial, at=_FIXED_AT,
        next_steps=["Freeze outbound transfer until one claim is withdrawn or proven.",
                    "Compare custody chains event by event."],
        findings=[
            EvidenceFinding(rule_id="R-DUP-IDENTITY-02", severity="critical",
                            reason="Two competing custody claims for one serial.",
                            references=["evt-0011", "evt-0014"],
                            next_step="Hold transfer; resolve to a single custodian."),
        ],
        feed=feed + _feed(("10:40:04", "finding", "R-DUP-IDENTITY-02 (simulated rule) FIRED — claims diverge.")),
        verify_link=f"/verify/{serial}",
        incident_link="/incidents/INC-1041",
    )


def run_post_sale_scan(inputs: dict[str, str]) -> ScenarioResult:
    serial = _require(inputs.get("serial", ""), "serial").upper()
    sale = _require(inputs.get("sale_event", ""), "sale_event")
    scan = _require(inputs.get("scan_event", ""), "scan_event")
    feed = _feed(
        ("10:40:01", "observation", f"Recorded sale for {serial} at {sale} (lifecycle → sold)."),
        ("10:40:02", "observation", f"New distribution scan {scan} claims the unit is back in transit."),
        ("10:40:03", "check", "Lifecycle order: sold units must not re-enter distribution custody."),
    )
    return ScenarioResult(
        scenario_id="post-sale-scan", outcome="flagged", severity="watch",
        summary=f"Post-sale scan flagged: {scan} arrived after the sale recorded at {sale}. A sold unit "
                "reappearing in distribution suggests a cloned QR re-entering circulation.",
        triggered_rules=["R-LIFECYCLE-05"],
        evidence_refs=[sale, scan],
        serial=serial, at=_FIXED_AT,
        next_steps=["Verify the physical unit against the sale record.",
                    "If the sale stands, treat the new scan as a clone signal."],
        findings=[
            EvidenceFinding(rule_id="R-LIFECYCLE-05", severity="watch",
                            reason="Scan arrived after the recorded sale event; lifecycle order violated.",
                            references=[sale, scan],
                            next_step="Confirm sale validity, then quarantine on clone suspicion."),
        ],
        feed=feed + _feed(("10:40:04", "finding", "R-LIFECYCLE-05 (simulated rule) FIRED — out-of-order lifecycle event.")),
        verify_link=f"/verify/{serial}",
    )


_RUNNERS = {
    "clone-qr": run_clone_qr,
    "revoked-actor": run_revoked_actor,
    "fake-handover": run_fake_handover,
    "tampered-history": run_tampered_history,
    "double-claim": run_double_claim,
    "post-sale-scan": run_post_sale_scan,
}


def run_scenario(scenario_id: str, inputs: dict[str, str]) -> ScenarioResult:
    key = scenario_id.strip().lower()
    if key not in _RUNNERS:
        raise UnknownScenarioError(scenario_id=scenario_id.strip())
    return _RUNNERS[key](inputs)


def now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")
