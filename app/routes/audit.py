"""Audit & Integrity routes: hash-chained audit log + verification."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routes import session
from app.services import deps

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/audit", response_class=HTMLResponse)
def audit_home(
    request: Request,
    outcome: str = Query(default="all"),
    action: str = Query(default=""),
    actor: str = Query(default=""),
) -> HTMLResponse:
    denied = session.guard(request, "integrity:view", "", active="audit")
    if denied is not None:
        return denied
    clean_outcome = outcome if outcome in ("all", "allowed", "denied", "rejected") else "all"
    return templates.TemplateResponse(
        request,
        "pages/audit.html",
        {**session.shell(request, "audit"),
         "events": deps.audit_events(outcome=clean_outcome, action=action, actor=actor),
         "report": deps.audit_verify(),
         "outcome": clean_outcome, "action": action, "actor": actor},
    )
