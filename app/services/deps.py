"""Service seam: mock-first demos, live chain backend for real serials."""

from __future__ import annotations

from app import config
from app.models.access import AccessOverview
from app.models.explorer import (
    AddressDetails,
    BlockDetails,
    ExplorerOverview,
    MerkleProof,
    SearchHit,
    TxDetails,
)
from app.models.lots import BlastRadius, LotAuditEntry, LotDetail, LotSummary
from app.models.operations import ActionLogEntry, IncidentDetail, OverviewData
from app.models.redteam import RedTeamLab, ScenarioResult
from app.models.verify import VerificationVerdict
from app.services import (
    chain_api,
    mock_access,
    mock_explorer,
    mock_lots,
    mock_operations,
    mock_redteam,
    mock_verify,
)

_DEMO_SERIALS = {"TT-DEMO-0001", "TT-DEMO-0002", "TT-DEMO-ERR"}


def get_verification(serial: str) -> VerificationVerdict:
    if config.is_demo() or serial.strip().upper() in _DEMO_SERIALS:
        return mock_verify.verify_serial(serial)
    return chain_api.verify_serial(serial)


def get_overview(severity: str = "all", status: str = "all", fail: bool = False) -> OverviewData:
    return mock_operations.get_overview(severity=severity, status=status, fail=fail)


def get_incident(incident_id: str) -> IncidentDetail:
    return mock_operations.get_incident(incident_id)


def record_incident_action(incident_id: str, action_id: str, note: str = "") -> ActionLogEntry:
    return mock_operations.record_action(incident_id, action_id, note=note)


def get_explorer_overview(page: int = 1, mode: str = "live") -> ExplorerOverview:
    return mock_explorer.get_overview(page=page, mode=mode)


def get_explorer_block(block_id: str) -> BlockDetails:
    return mock_explorer.get_block(block_id)


def get_explorer_tx(tx_hash: str) -> TxDetails:
    return mock_explorer.get_tx(tx_hash)


def get_explorer_address(address: str) -> AddressDetails:
    return mock_explorer.get_address(address)


def search_explorer(query: str) -> list[SearchHit]:
    return mock_explorer.search(query)


def get_merkle_proof(tx_hash: str, verify: bool = False) -> MerkleProof:
    return mock_explorer.get_proof(tx_hash, verify=verify)


def get_tampered_proof_demo() -> MerkleProof:
    """Test-only tampered vector: same leaf, one corrupted sibling -> INVALID."""
    return mock_explorer.tampered_proof_demo()


def get_redteam_lab(run_state: dict[str, bool] | None = None) -> RedTeamLab:
    return mock_redteam.get_lab(run_state)


def run_redteam_scenario(scenario_id: str, inputs: dict[str, str]) -> ScenarioResult:
    return mock_redteam.run_scenario(scenario_id, inputs)


def list_lots(query: str = "", freeze: str = "all", fail: bool = False) -> list[LotSummary]:
    if config.is_demo():
        return mock_lots.list_lots(query=query, freeze=freeze, fail=fail)
    return chain_api.list_lots(query=query, freeze=freeze)


def get_lot(lot_id: str) -> LotDetail:
    if config.is_demo() or lot_id.strip().upper() in chain_api._DEMO_LOT_IDS:
        return mock_lots.get_lot(lot_id)
    return chain_api.get_lot(lot_id)


def get_blast_radius(lot_id: str) -> BlastRadius:
    if config.is_demo() or lot_id.strip().upper() in chain_api._DEMO_LOT_IDS:
        return mock_lots.get_blast_radius(lot_id)
    return chain_api.get_blast_radius(lot_id)


def freeze_lot(lot_id: str, reason: str = "", role: str = "verifier") -> LotAuditEntry:
    if config.is_demo() or lot_id.strip().upper() in chain_api._DEMO_LOT_IDS:
        return mock_lots.freeze_lot(lot_id, reason)
    return chain_api.freeze_lot(lot_id, reason, role)


def recall_lot(lot_id: str, reason: str = "", role: str = "verifier") -> LotAuditEntry:
    if config.is_demo() or lot_id.strip().upper() in chain_api._DEMO_LOT_IDS:
        return mock_lots.recall_lot(lot_id, reason)
    return chain_api.recall_lot(lot_id, reason, role)


def access_overview(role_id: str | None) -> AccessOverview:
    return mock_access.overview(role_id)


def access_require(role_id: str | None, permission: str, target: str = "") -> str:
    return mock_access.require(role_id, permission, target)


def access_can(role_id: str | None, permission: str) -> bool:
    return mock_access.can(role_id, permission)


def access_role_id(role_id: str | None) -> str:
    return mock_access.normalize_role(role_id)


def access_record_allowed(role_id: str | None, permission: str, target: str = "") -> None:
    mock_access.record_allowed(role_id, permission, target)
