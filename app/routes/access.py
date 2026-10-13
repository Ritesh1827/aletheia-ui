"""Access Control routes: permission matrix, demo session roles, access audit."""

from __future__ import annotations

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.routes import session
from app.routes.session import SESSION_COOKIE
from app.services import deps

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class RoleNotice(BaseModel):
    kind: str
    text: str


def _safe_next(next_url: str) -> str:
    target = (next_url or "").strip()
    if target.startswith("/") and not target.startswith("//"):
        return target
    return "/access"


@router.get("/access", response_class=HTMLResponse)
def access_home(request: Request, notice: str = Query(default="")) -> HTMLResponse:
    role_id = session.current_role(request)
    flash = None
    if notice == "role":
        data = deps.access_overview(role_id)
        flash = RoleNotice(
            kind="info",
            text=f"Demo session now acts as {data.current_role.name}. "
                 "This is a labelled demo switch, not identity verification.",
        )
    return templates.TemplateResponse(
        request,
        "pages/access.html",
        {**session.shell(request, "access"), "overview": deps.access_overview(role_id),
         "flash": flash},
    )


@router.post("/access/role", include_in_schema=False)
def switch_role(
    role_id: str = Form(default="verifier"),
    next_url: str = Form(default="/access", alias="next"),
) -> Response:
    """Demo role switch: normalize the requested role and persist it in a cookie.

    Unknown role IDs fall back to the read-only verifier — a spoofed value
    can never escalate beyond the four demo roles, and the switch is labelled
    as a demo convenience everywhere it appears.
    """
    normalized = deps.access_role_id(role_id)
    actor = str(deps.access_overview(normalized).current_user.id)
    deps.audit_record(actor, "session:switch-role", normalized, "allowed", {})
    target = _safe_next(next_url)
    sep = "&" if "?" in target else "?"
    response = Response(status_code=303, headers={"Location": f"{target}{sep}notice=role"})
    response.set_cookie(SESSION_COOKIE, normalized, httponly=True, samesite="lax")
    return response
