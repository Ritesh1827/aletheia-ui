"""Mock explorer service. Fixtures stay consistent with Verify + Tower mocks."""

from __future__ import annotations

import hashlib

from app.models.explorer import (
    AddressDetails,
    AnchorSummary,
    BlockDetails,
    ContractEvent,
    ExplorerLot,
    ExplorerOverview,
    MerkleProof,
    NetworkStatus,
    ProofStep,
    RegistryEvent,
    SearchHit,
    TxDetails,
    TxRow,
)

TX_A = "0x7a3f9c1e5b2846d0a9c4e71f3b8d2a6c5e0f1a2b"
TX_B = "0x3d8b21f64a07c9e15d0f42a8c6e9b3d715c8a4"
TX_C = "0x9e41c0a7d2b56f18390c4e6a1d7b3f05c2d8e6"
CONTRACT = "0x4f2ad19c6b3871e05ddc4a29f7c3e608b1a5d7"
ACTOR_NORTHWIND = "0x8c3d2f1a9b4e5c60718293a4b5d6e7f8091a2"
ACTOR_UNKNOWN = "0x000000000000000000000000000000000000dEaD"
BLOCK_A = 1841204
BLOCK_B = 1845517
BLOCK_C = 1845520


def _fake_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:40]


def _build_proof_path(anchor_id: str, first_event: str) -> tuple[str, list[ProofStep], str]:
    """Derive a deterministic, self-consistent demo proof path (leaf -> root)."""
    leaf = _fake_hash(anchor_id, first_event)
    steps = [
        ProofStep(sibling=_fake_hash(anchor_id, f"sib-{i}"),
                  direction="right" if i % 2 == 0 else "left")
        for i in range(3)
    ]
    h = leaf
    for step in steps:
        pair = h + step.sibling if step.direction == "right" else step.sibling + h
        h = _fake_hash(pair)
    return leaf, steps, h


_LEAF_A, _STEPS_A, ROOT_A = _build_proof_path("ANCH-DEMO-1", "evt-0001")
_LEAF_B, _STEPS_B, ROOT_B = _build_proof_path("ANCH-DEMO-2", "evt-0010")

TAMPERED_LEAF = _LEAF_B
TAMPERED_STEPS = [
    step if i != 1 else ProofStep(sibling="f" * 40, direction=step.direction)
    for i, step in enumerate(_STEPS_B)
]


class UnknownRecordError(Exception):
    def __init__(self, record: str) -> None:
        super().__init__(f"Unknown explorer record: {record}")
        self.record = record


class ExplorerBackendError(Exception):
    def __init__(self, correlation_id: str) -> None:
        super().__init__("Simulated explorer backend failure")
        self.correlation_id = correlation_id


def network_status(mode: str = "live") -> NetworkStatus:
    if mode == "down":
        return NetworkStatus(
            network_name="Aletheia local demo network",
            chain_id="31337",
            rpc="disconnected",
            latest_block=None,
            latest_anchor=None,
            pending_batches=0,
            contract=CONTRACT,
            freshness="unavailable",
            retrieved_at="2026-10-12 09:20 UTC",
        )
    if mode == "stale":
        return NetworkStatus(
            network_name="Aletheia local demo network",
            chain_id="31337",
            rpc="connected",
            latest_block=BLOCK_B,
            latest_anchor="ANCH-DEMO-2",
            pending_batches=1,
            contract=CONTRACT,
            freshness="stale",
            retrieved_at="2026-10-11 22:04 UTC",
        )
    return NetworkStatus(
        network_name="Aletheia local demo network",
        chain_id="31337",
        rpc="connected",
        latest_block=BLOCK_C,
        latest_anchor="ANCH-DEMO-2",
        pending_batches=1,
        contract=CONTRACT,
        freshness="live",
        retrieved_at="2026-10-12 09:20 UTC",
    )


def anchors() -> list[AnchorSummary]:
    return [
        AnchorSummary(
            anchor_id="ANCH-DEMO-2", block=BLOCK_B, tx_hash=TX_B,
            time="2026-10-02 08:11 UTC", root=ROOT_B, event_count=488,
            lot_id="LOT-DEMO-A", serials=["AL-DEMO-0002"], state="anchored",
        ),
        AnchorSummary(
            anchor_id="ANCH-DEMO-1", block=BLOCK_A, tx_hash=TX_A,
            time="2026-09-03 07:52 UTC", root=ROOT_A, event_count=512,
            lot_id="LOT-DEMO-A", serials=["AL-DEMO-0001"], state="anchored",
        ),
        AnchorSummary(
            anchor_id="BATCH-PENDING-3", block=None, tx_hash=None,
            time="—", root="", event_count=96,
            lot_id="LOT-DEMO-B", serials=[], state="pending",
        ),
    ]


def registry_events() -> list[RegistryEvent]:
    return [
        RegistryEvent(kind="BatchAnchor", time="2026-10-02 08:11 UTC",
                      actor=CONTRACT, summary="Anchored batch ANCH-DEMO-2 (488 leaves).",
                      ref=TX_B),
        RegistryEvent(kind="ActorStatus", time="2026-09-29 15:44 UTC",
                      actor="registrar", summary="Scanner held unregistered — see INC-1038.",
                      ref="INC-1038"),
        RegistryEvent(kind="LotRegistration", time="2026-08-02 10:00 UTC",
                      actor="Acme Manufacturing", summary="Registered LOT-DEMO-A (10,000 units).",
                      ref="LOT-DEMO-A"),
        RegistryEvent(kind="BatchAnchor", time="2026-09-03 07:52 UTC",
                      actor=CONTRACT, summary="Anchored batch ANCH-DEMO-1 (512 leaves).",
                      ref=TX_A),
    ]


def explorer_lots() -> list[ExplorerLot]:
    return [
        ExplorerLot(lot_id="LOT-DEMO-A", committed_qty=10000, freeze_state="Not frozen",
                    root=ROOT_B, last_anchor="ANCH-DEMO-2", serials_count=2),
        ExplorerLot(lot_id="LOT-DEMO-B", committed_qty=2500, freeze_state="Not frozen",
                    root="", last_anchor="BATCH-PENDING-3", serials_count=0),
    ]


def get_overview(page: int = 1, mode: str = "live") -> ExplorerOverview:
    if mode == "error":
        raise ExplorerBackendError(correlation_id="demo-corr-77e0")
    per_page = 2
    all_anchors = anchors()
    pages = max(1, (len(all_anchors) + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    window = all_anchors[(page - 1) * per_page: page * per_page]
    return ExplorerOverview(
        network=network_status(mode),
        anchors=window,
        events=registry_events(),
        lots=explorer_lots(),
        anchor_page=page,
        anchor_pages=pages,
    )


def get_block(block_id: str) -> BlockDetails:
    key = block_id.strip().lower()
    if key in {"1841204", "0xaaa111"}:
        return BlockDetails(
            height=BLOCK_A,
            block_hash="0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1",
            parent_hash="0x9990009990009990009990009990009990009990",
            time="2026-09-03 07:52 UTC",
            tx_count=3,
            anchor_id="ANCH-DEMO-1",
            gas_used=None,
            txs=[
                TxRow(tx_hash=TX_A, method="anchorBatch", sender=ACTOR_NORTHWIND,
                      status="success", lot_id="LOT-DEMO-A"),
                TxRow(tx_hash="0x1111111111111111111111111111111111111111",
                      method="registerLot", sender=CONTRACT, status="success",
                      lot_id="LOT-DEMO-A"),
                TxRow(tx_hash="0x2222222222222222222222222222222222222222",
                      method="setActorStatus", sender=CONTRACT, status="success"),
            ],
        )
    if key in {"1845517", "0xbbb222"}:
        return BlockDetails(
            height=BLOCK_B,
            block_hash="0xbbb222bbb222bbb222bbb222bbb222bbb222bbb2",
            parent_hash="0xaaa111aaa111aaa111aaa111aaa111aaa111aaa1",
            time="2026-10-02 08:11 UTC",
            tx_count=2,
            anchor_id="ANCH-DEMO-2",
            gas_used=None,
            txs=[
                TxRow(tx_hash=TX_B, method="anchorBatch", sender=ACTOR_NORTHWIND,
                      status="success", lot_id="LOT-DEMO-A"),
                TxRow(tx_hash=TX_C, method="anchorBatch", sender=ACTOR_NORTHWIND,
                      status="pending", lot_id="LOT-DEMO-B"),
            ],
        )
    raise UnknownRecordError(record=block_id.strip())


def get_tx(tx_hash: str) -> TxDetails:
    key = tx_hash.strip().lower()
    if key == TX_A.lower():
        return TxDetails(
            tx_hash=TX_A, status="success", block=BLOCK_A, time="2026-09-03 07:52 UTC",
            sender=ACTOR_NORTHWIND, contract=CONTRACT, method="anchorBatch",
            lot_id="LOT-DEMO-A", anchor_id="ANCH-DEMO-1", root=ROOT_A, leaf_count=512,
            events=[
                ContractEvent(name="BatchAnchored",
                              detail="anchor ANCH-DEMO-1 · root 9f2c…41ab · 512 leaves"),
                ContractEvent(name="LotCommitted",
                              detail="LOT-DEMO-A commitment reconfirmed"),
            ],
            offchain_ids=["evt-0001", "evt-0002", "evt-0003", "evt-0004", "evt-0005", "evt-0006"],
            payload_missing=False, proof_status="NOT VERIFIED",
            serials=["AL-DEMO-0001"], incident_id=None,
        )
    if key == TX_B.lower():
        return TxDetails(
            tx_hash=TX_B, status="success", block=BLOCK_B, time="2026-10-02 08:11 UTC",
            sender=ACTOR_NORTHWIND, contract=CONTRACT, method="anchorBatch",
            lot_id="LOT-DEMO-A", anchor_id="ANCH-DEMO-2", root=ROOT_B, leaf_count=488,
            events=[
                ContractEvent(name="BatchAnchored",
                              detail="anchor ANCH-DEMO-2 · root c41d…02cd · 488 leaves"),
            ],
            offchain_ids=["evt-0010", "evt-0011", "evt-0012", "evt-0013", "evt-0014"],
            payload_missing=False, proof_status="NOT VERIFIED",
            serials=["AL-DEMO-0002"], incident_id="INC-1042",
        )
    if key == TX_C.lower():
        return TxDetails(
            tx_hash=TX_C, status="pending", block=None, time="—",
            sender=ACTOR_NORTHWIND, contract=CONTRACT, method="anchorBatch",
            lot_id="LOT-DEMO-B", anchor_id="BATCH-PENDING-3", root="", leaf_count=96,
            events=[], offchain_ids=[],
            payload_missing=True, proof_status="NOT VERIFIED",
            serials=[], incident_id=None,
        )
    raise UnknownRecordError(record=tx_hash.strip())


def get_address(address: str) -> AddressDetails:
    key = address.strip().lower()
    if key == ACTOR_NORTHWIND.lower():
        return AddressDetails(
            address=ACTOR_NORTHWIND, kind="actor", label="Northwind Logistics (registered)",
            status="Active", registered_at="2026-07-18",
            related_anchors=["ANCH-DEMO-1", "ANCH-DEMO-2"],
            related_txs=[TX_A, TX_B, TX_C],
        )
    if key == CONTRACT.lower():
        return AddressDetails(
            address=CONTRACT, kind="contract", label="Provenance registry (demo contract)",
            status="Deployed on local demo network",
            related_anchors=["ANCH-DEMO-1", "ANCH-DEMO-2"],
            related_txs=[TX_A, TX_B],
        )
    if key == ACTOR_UNKNOWN.lower():
        return AddressDetails(
            address=ACTOR_UNKNOWN, kind="actor", label="Unknown claimant (unregistered)",
            status="Revoked — see INC-1041",
            related_anchors=[], related_txs=[],
        )
    raise UnknownRecordError(record=address.strip())


def search(query: str) -> list[SearchHit]:
    q = query.strip()
    ql = q.lower()
    hits: list[SearchHit] = []
    if ql in {"1841204", "0xaaa111"}:
        hits.append(SearchHit(kind="Block", label=f"Block {BLOCK_A}",
                              detail="3 transactions · ANCH-DEMO-1", link="/explorer/block/1841204"))
    if ql in {"1845517", "0xbbb222"}:
        hits.append(SearchHit(kind="Block", label=f"Block {BLOCK_B}",
                              detail="2 transactions · ANCH-DEMO-2", link="/explorer/block/1845517"))
    for tx, lot in ((TX_A, "LOT-DEMO-A"), (TX_B, "LOT-DEMO-A"), (TX_C, "LOT-DEMO-B")):
        if ql == tx.lower():
            hits.append(SearchHit(kind="Transaction", label=f"{tx[:14]}…{tx[-8:]}",
                                  detail=f"anchor batch · {lot}", link=f"/explorer/tx/{tx}"))
    for root, anchor in ((ROOT_A, "ANCH-DEMO-1"), (ROOT_B, "ANCH-DEMO-2")):
        if ql == root.lower():
            hits.append(SearchHit(kind="Merkle root", label=f"{root[:14]}…{root[-8:]}",
                                  detail=f"anchored by {anchor}", link="/explorer"))
    if ql in {"lot-demo-a", "lot-demo-b"}:
        hits.append(SearchHit(kind="Lot", label=q.upper(),
                              detail="committed lot with recent anchors", link="/explorer"))
    if ql in {"al-demo-0001", "al-demo-0002"}:
        hits.append(SearchHit(kind="Serial", label=q.upper(),
                              detail="verify this serial with full evidence", link=f"/verify/{q.upper()}"))
    if ql in {ACTOR_NORTHWIND.lower(), CONTRACT.lower(), ACTOR_UNKNOWN.lower()}:
        hits.append(SearchHit(kind="Address", label=f"{q[:14]}…{q[-8:]}",
                              detail="actor or contract record", link=f"/explorer/address/{q}"))
    return hits


def _proof_for(anchor_id: str, root: str, leaf: str, steps: list[ProofStep],
               verify: bool) -> MerkleProof:
    if not verify:
        return MerkleProof(
            leaf=leaf, steps=steps, computed_root="", expected_root=root,
            status="NOT VERIFIED",
            explanation="Proof loaded but not verified. Run verification to compare "
                        "the computed root against the anchored root.",
        )
    h = leaf
    for step in steps:
        pair = h + step.sibling if step.direction == "right" else step.sibling + h
        h = _fake_hash(pair)
    match = h == root
    return MerkleProof(
        leaf=leaf, steps=steps, computed_root=h, expected_root=root,
        status="PROOF VALID" if match else "PROOF INVALID",
        explanation=("Computed root matches the anchored root, so this leaf is included "
                     "in the batch."
                     if match else
                     "Computed root differs from the anchored root — treat inclusion as "
                     "unproven and inspect the batch leaves."),
    )


def tampered_proof_demo() -> MerkleProof:
    """Corrupted-sibling vector used by tests to exercise the INVALID path."""
    return _proof_for("ANCH-DEMO-2", ROOT_B, TAMPERED_LEAF, TAMPERED_STEPS, verify=True)


def get_proof(tx_hash: str, verify: bool = False) -> MerkleProof:
    key = tx_hash.strip().lower()
    if key == TX_A.lower():
        return _proof_for("ANCH-DEMO-1", ROOT_A, _LEAF_A, _STEPS_A, verify)
    if key == TX_B.lower():
        return _proof_for("ANCH-DEMO-2", ROOT_B, _LEAF_B, _STEPS_B, verify)
    detail = get_tx(tx_hash)
    if detail.payload_missing or not detail.root:
        return MerkleProof(
            leaf="", steps=[], computed_root="", expected_root="",
            status="NOT VERIFIED",
            explanation="No anchored payload exists for this transaction yet, so there "
                        "is nothing to verify against.",
        )
    return _proof_for(detail.anchor_id, detail.root,
                       _fake_hash(detail.anchor_id, "evt"), [], verify)
