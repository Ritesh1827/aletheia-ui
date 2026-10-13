"""Mock access service. Demo session roles, permissions, and audit.

There is no production authentication here. The "session" is a demo role
selected via query parameter (`?as=`) or cookie (`al_role`), defaulting to
the read-only verifier. Every privileged decision goes through
`require()` on the backend — never trust hidden buttons.
"""

from __future__ import annotations

from app.models.access import (
    PERMISSIONS,
    AccessAuditEntry,
    AccessOverview,
    DemoUser,
    RoleDetail,
)

_DEMO_AT = "2026-10-12T12:00:00Z"

_ROLE_PERMS: dict[str, list[str]] = {
    "verifier": ["verify:public"],
    "operator": ["verify:public", "redteam:run"],
    "investigator": [
        "verify:public",
        "evidence:internal",
        "incident:annotate",
        "lot:freeze",
        "redteam:run",
        "integrity:view",
    ],
    "admin": [
        "verify:public",
        "evidence:internal",
        "incident:annotate",
        "lot:freeze",
        "lot:recall",
        "actor:revoke",
        "redteam:run",
        "integrity:view",
    ],
}

_ROLES: dict[str, RoleDetail] = {
    "verifier": RoleDetail(
        id="verifier", name="Read-only Verifier",
        purpose="Public serial verification only. Cannot annotate, freeze, recall, or run scenarios.",
        permissions=_ROLE_PERMS["verifier"],
    ),
    "operator": RoleDetail(
        id="operator", name="Operator",
        purpose="Verify serials and execute Red-Team scenarios in the protected demo environment.",
        permissions=_ROLE_PERMS["operator"],
    ),
    "investigator": RoleDetail(
        id="investigator", name="Investigator",
        purpose="Read incidents and evidence, annotate cases, and freeze lots pending review. "
                "Can recommend — but not execute — recalls.",
        permissions=_ROLE_PERMS["investigator"],
    ),
    "admin": RoleDetail(
        id="admin", name="Admin",
        purpose="Full demo authority: freeze and recall lots, revoke actors, and manage response. "
                "Least privilege still applies — no silent self-elevation.",
        permissions=_ROLE_PERMS["admin"],
    ),
}

_USERS: list[DemoUser] = [
    DemoUser(id="demo.verifier", name="Demo Verifier", role_id="verifier",
             organization="Public demo"),
    DemoUser(id="demo.operator", name="Demo Operator", role_id="operator",
             organization="Demo operations"),
    DemoUser(id="demo.investigator", name="Demo Investigator", role_id="investigator",
             organization="Demo investigations"),
    DemoUser(id="demo.admin", name="Demo Admin", role_id="admin",
             organization="Demo administration"),
]

_AUDIT: list[AccessAuditEntry] = [
    AccessAuditEntry(at="2026-10-12 09:40 UTC", actor="demo.verifier",
                     action="incident:annotate", target="INC-1042",
                     outcome="allowed", request_id="demo-req-0001"),
    AccessAuditEntry(at="2026-10-12 11:00 UTC", actor="demo.recall-manager",
                     action="lot:freeze", target="LOT-DEMO-A",
                     outcome="allowed", request_id="demo-req-0002"),
]


class ForbiddenError(Exception):
    def __init__(self, permission: str, role_id: str) -> None:
        super().__init__(f"Role '{role_id}' lacks permission '{permission}'.")
        self.permission = permission
        self.role_id = role_id


def normalize_role(role_id: str | None) -> str:
    key = (role_id or "").strip().lower()
    if key == "readonly":
        key = "verifier"
    if key == "recall-manager":
        key = "admin"
    return key if key in _ROLE_PERMS else "verifier"


def role_for(role_id: str | None) -> RoleDetail:
    return _ROLES[normalize_role(role_id)]


def user_for(role_id: str | None) -> DemoUser:
    key = normalize_role(role_id)
    for user in _USERS:
        if user.role_id == key:
            return user
    return _USERS[0]


def can(role_id: str | None, permission: str) -> bool:
    return permission in _ROLE_PERMS.get(normalize_role(role_id), [])


def require(role_id: str | None, permission: str, target: str = "") -> str:
    """Enforce a permission. Returns the normalized role or raises ForbiddenError."""
    key = normalize_role(role_id)
    if permission not in _ROLE_PERMS[key]:
        _AUDIT.append(AccessAuditEntry(
            at=_DEMO_AT, actor=user_for(key).id, action=permission,
            target=target, outcome="denied", request_id=f"demo-req-{len(_AUDIT) + 1:04d}",
        ))
        raise ForbiddenError(permission=permission, role_id=key)
    return key


def record_allowed(role_id: str | None, permission: str, target: str = "") -> AccessAuditEntry:
    key = normalize_role(role_id)
    entry = AccessAuditEntry(
        at=_DEMO_AT, actor=user_for(key).id, action=permission,
        target=target, outcome="allowed", request_id=f"demo-req-{len(_AUDIT) + 1:04d}",
    )
    _AUDIT.append(entry)
    return entry


def overview(role_id: str | None) -> AccessOverview:
    key = normalize_role(role_id)
    matrix = {perm: {rid: (perm in perms) for rid, perms in _ROLE_PERMS.items()}
              for perm in PERMISSIONS}
    return AccessOverview(
        current_role=_ROLES[key],
        current_user=user_for(key),
        roles=[_ROLES[rid] for rid in ("verifier", "operator", "investigator", "admin")],
        users=list(_USERS),
        permissions=list(PERMISSIONS),
        matrix=matrix,
        audit=list(reversed(_AUDIT)),
        is_demo=True,
    )


def reset_demo_state() -> None:
    _AUDIT[:] = [
        AccessAuditEntry(at="2026-10-12 09:40 UTC", actor="demo.verifier",
                         action="incident:annotate", target="INC-1042",
                         outcome="allowed", request_id="demo-req-0001"),
        AccessAuditEntry(at="2026-10-12 11:00 UTC", actor="demo.recall-manager",
                         action="lot:freeze", target="LOT-DEMO-A",
                         outcome="allowed", request_id="demo-req-0002"),
    ]
