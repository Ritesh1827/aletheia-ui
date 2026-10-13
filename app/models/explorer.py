"""Pydantic models for the Provenance Block Explorer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RpcState = Literal["connected", "disconnected"]
Freshness = Literal["live", "stale", "unavailable"]
AnchorState = Literal["anchored", "pending"]
TxState = Literal["success", "pending", "failed"]
ProofState = Literal["PROOF VALID", "PROOF INVALID", "NOT VERIFIED"]


class NetworkStatus(BaseModel):
    network_name: str
    chain_id: str
    rpc: RpcState
    latest_block: int | None = None
    latest_anchor: str | None = None
    pending_batches: int = 0
    contract: str | None = None
    freshness: Freshness = "live"
    retrieved_at: str = ""


class AnchorSummary(BaseModel):
    anchor_id: str
    block: int | None = None
    tx_hash: str | None = None
    time: str = ""
    root: str = ""
    event_count: int = 0
    lot_id: str = ""
    serials: list[str] = Field(default_factory=list)
    state: AnchorState = "anchored"


class RegistryEvent(BaseModel):
    kind: str
    time: str
    actor: str
    summary: str
    ref: str = ""


class ExplorerLot(BaseModel):
    lot_id: str
    committed_qty: int
    freeze_state: str
    root: str
    last_anchor: str
    serials_count: int


class TxRow(BaseModel):
    tx_hash: str
    method: str
    sender: str
    status: TxState
    lot_id: str = ""


class BlockDetails(BaseModel):
    height: int
    block_hash: str
    parent_hash: str
    time: str
    tx_count: int
    txs: list[TxRow] = Field(default_factory=list)
    anchor_id: str = ""
    gas_used: int | None = None


class ContractEvent(BaseModel):
    name: str
    detail: str


class TxDetails(BaseModel):
    tx_hash: str
    status: TxState
    block: int | None = None
    time: str = ""
    sender: str = ""
    contract: str = ""
    method: str = ""
    lot_id: str = ""
    anchor_id: str = ""
    root: str = ""
    leaf_count: int = 0
    events: list[ContractEvent] = Field(default_factory=list)
    offchain_ids: list[str] = Field(default_factory=list)
    payload_missing: bool = False
    proof_status: ProofState = "NOT VERIFIED"
    serials: list[str] = Field(default_factory=list)
    incident_id: str | None = None


class ProofStep(BaseModel):
    sibling: str
    direction: Literal["left", "right"]


class MerkleProof(BaseModel):
    leaf: str
    steps: list[ProofStep] = Field(default_factory=list)
    computed_root: str = ""
    expected_root: str = ""
    status: ProofState = "NOT VERIFIED"
    explanation: str = ""


class AddressDetails(BaseModel):
    address: str
    kind: Literal["actor", "contract"]
    label: str
    status: str
    registered_at: str = ""
    related_anchors: list[str] = Field(default_factory=list)
    related_txs: list[str] = Field(default_factory=list)


class SearchHit(BaseModel):
    kind: str
    label: str
    detail: str
    link: str


class ExplorerOverview(BaseModel):
    network: NetworkStatus
    anchors: list[AnchorSummary]
    events: list[RegistryEvent]
    lots: list[ExplorerLot]
    anchor_page: int = 1
    anchor_pages: int = 1
    query: str = ""
    hits: list[SearchHit] = Field(default_factory=list)
