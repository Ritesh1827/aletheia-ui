"""Mock audit service: hash-chained audit log + integrity verification.

Every privileged action appends an event; each record commits to the hash of
the previous one, so altered records or broken links are detectable by
recomputation. Verification runs on demand in this backend — the browser
never computes validity. Only non-sensitive context is stored: identifiers,
action names, outcomes, and presence flags. Free-text notes and reasons stay
out of this log (lot-scoped logs keep their own demo records).
"""

from __future__ import annotations

import hashlib
import json

from app.models.audit import AuditEvent, IntegrityFailure, IntegrityReport

_GENESIS = "GENESIS"
_DEMO_CLOCK = "2026-10-12T12:{:02d}:{:02d}Z"

_LOG: list[AuditEvent] = []


def _canonical(event: AuditEvent) -> str:
    return "|".join([
        str(event.seq),
        event.event_id,
        event.at,
        event.actor,
        event.action,
        event.target,
        event.outcome,
        json.dumps(event.context, sort_keys=True),
        event.prev_hash,
    ])


def _digest(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stamp(seq: int) -> str:
    return _DEMO_CLOCK.format((seq // 60) % 60, seq % 60)


def record(
    actor: str,
    action: str,
    target: str = "",
    outcome: str = "allowed",
    context: dict[str, str] | None = None,
) -> AuditEvent:
    seq = len(_LOG) + 1
    prev = _LOG[-1].record_hash if _LOG else _GENESIS
    event = AuditEvent(
        seq=seq,
        event_id=f"EVT-{seq:04d}",
        at=_stamp(seq),
        actor=actor,
        action=action,
        target=target,
        outcome=outcome,
        context=dict(context or {}),
        prev_hash=prev,
    )
    event.record_hash = _digest(_canonical(event))
    _LOG.append(event)
    return event


def events(
    outcome: str = "all",
    action: str = "",
    actor: str = "",
) -> list[AuditEvent]:
    result = list(_LOG)
    if outcome != "all":
        result = [e for e in result if e.outcome == outcome]
    if action.strip():
        needle = action.strip().lower()
        result = [e for e in result if needle in e.action.lower()]
    if actor.strip():
        needle = actor.strip().lower()
        result = [e for e in result if needle in e.actor.lower()]
    return list(reversed(result))


def verify() -> IntegrityReport:
    """Recompute every record hash and link. PASS only on a clean run."""
    if not _LOG:
        return IntegrityReport(
            status="NOT VERIFIED",
            checked=0,
            note="No audit records exist yet — perform a privileged action first. "
                 "Absence of records is reported as unverified, never as passing.",
        )
    failures: list[IntegrityFailure] = []
    prev = _GENESIS
    for event in _LOG:
        if event.prev_hash != prev:
            failures.append(IntegrityFailure(
                seq=event.seq, event_id=event.event_id,
                reason="broken link: previous hash does not match the prior record",
                expected=prev, actual=event.prev_hash,
            ))
        recomputed = _digest(_canonical(event))
        if recomputed != event.record_hash:
            failures.append(IntegrityFailure(
                seq=event.seq, event_id=event.event_id,
                reason="altered record: stored hash does not match recomputed content",
                expected=recomputed, actual=event.record_hash,
            ))
        prev = event.record_hash
    if failures:
        return IntegrityReport(
            status="FAIL", checked=len(_LOG), failures=failures,
            verified_at=_stamp(len(_LOG)),
            note=f"{len(failures)} integrity problem(s) across {len(_LOG)} records. "
                 "Treat the affected history as unproven.",
        )
    return IntegrityReport(
        status="PASS", checked=len(_LOG),
        verified_at=_stamp(len(_LOG)),
        note=f"All {len(_LOG)} records recomputed cleanly against the hash chain. "
             "This verifies record integrity only — not physical authenticity.",
    )


def tamper_demo(seq: int, field: str, value: str) -> bool:
    """Test-only helper: mutate a stored record without updating its hash.

    Simulates a tampered ledger so tests can prove detection works. Never
    called by routes or templates.
    """
    for event in _LOG:
        if event.seq == seq and field in {"actor", "action", "target", "outcome"}:
            setattr(event, field, value)
            return True
    return False


def seed_demo_history() -> None:
    record("demo.verifier", "incident:annotate", "INC-1042", "allowed",
           {"action": "note"})
    record("demo.admin", "lot:freeze", "LOT-DEMO-A", "allowed",
           {"reason_given": "false"})


def reset_demo_state() -> None:
    _LOG.clear()
    seed_demo_history()


seed_demo_history()
