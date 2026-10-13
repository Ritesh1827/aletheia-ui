"""Demo session helper: role resolution + backend permission guard.

The session is a demo role carried on `?as=` or the `al_role` cookie,
defaulting to the read-only verifier. `guard()` enforces permissions on the
backend and renders a 403 page on denial — UI hiding is never the boundary.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.services import deps
from app.services.mock_access import ForbiddenError

templates = Jinja2Templates(directory="templates")

SESSION_COOKIE = "al_role"


def current_role(request: Request) -> str:
    query_role = request.query_params.get("as")
    if query_role:
        return deps.access_role_id(query_role)
    return deps.access_role_id(request.cookies.get(SESSION_COOKIE))


def actor_id(request: Request) -> str:
    """Demo actor identity for audit records (never a secret)."""
    return str(deps.access_overview(current_role(request)).current_user.id)


def session_context(request: Request) -> dict[str, object]:
    role_id = current_role(request)
    data = deps.access_overview(role_id)
    return {
        "demo": config.is_demo(),
        "chain_label": config.chain_label(),
        "role_id": role_id,
        "role_name": data.current_role.name,
        "user_name": data.current_user.name,
        "user_org": data.current_user.organization,
        "can": lambda permission: deps.access_can(role_id, permission),
    }


def shell(request: Request, active: str) -> dict[str, object]:
    """Shared template context: demo flags plus current demo session."""
    return {**session_context(request), "active": active}


def guard(
    request: Request,
    permission: str,
    target: str = "",
    active: str = "access",
) -> HTMLResponse | None:
    """Require a permission for the current demo session.

    Returns None when allowed (and records the audit entry), otherwise a
    403 response that names the missing permission without leaking data.
    """
    role_id = current_role(request)
    try:
        deps.access_require(role_id, permission, target)
    except ForbiddenError as exc:
        actor = str(deps.access_overview(role_id).current_user.id)
        deps.audit_record(actor, permission, target, "denied", {})
        data = deps.access_overview(role_id)
        return templates.TemplateResponse(
            request,
            "pages/forbidden.html",
            {**session_context(request), "active": active,
             "permission": exc.permission, "role": data.current_role,
             "target": target},
            status_code=403,
        )
    deps.access_record_allowed(role_id, permission, target)
    return None
