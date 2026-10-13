"""Demo session helper: role resolution + backend permission guard.

The session is a demo role carried on `?as=` or the `tt_role` cookie,
defaulting to the read-only verifier. `guard()` enforces permissions on the
backend and renders a 403 page on denial — UI hiding is never the boundary.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.services import deps
from app.services.mock_access import ForbiddenError

templates = Jinja2Templates(directory="templates")

SESSION_COOKIE = "tt_role"


def current_role(request: Request) -> str:
    query_role = request.query_params.get("as")
    if query_role:
        return deps.access_role_id(query_role)
    return deps.access_role_id(request.cookies.get(SESSION_COOKIE))


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


router = APIRouter()


@router.post("/session/role", include_in_schema=False)
async def switch_role(request: Request) -> Response:
    form = await request.form()
    role = str(form.get("role", "verifier"))[:32]
    nxt = str(form.get("next", request.headers.get("referer", "/")))[:256]
    role_id = deps.access_role_id(role)
    dest = nxt if nxt.startswith("/") else "/"
    resp = RedirectResponse(url=dest, status_code=303)
    resp.set_cookie(SESSION_COOKIE, role_id, httponly=True, samesite="lax")
    return resp
