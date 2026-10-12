"""Overview + incident routes (M2). Reuses Verify shell and components."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import config
from app.models.verify import VERDICT_CAVEAT
from app.services import deps
from app.services.mock_operations import MockOperationsError, UnknownIncidentError

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class Notice(BaseModel):
    kind: str
    text: str


def shell(active: str) -> dict[str, object]:
    return {
        "demo": config.is_demo(),
        "chain_label": config.chain_label(),
        "active": active,
    }


@router.get("/overview", response_class=HTMLResponse)
def overview(
    request: Request,
    severity: str = Query(default="all"),
    status: str = Query(default="all"),
    fail: str = Query(default=""),
) -> HTMLResponse:
    try:
        data = deps.get_overview(severity=severity, status=status, fail=(fail == "1"))
    except MockOperationsError as exc:
        return templates.TemplateResponse(
            request,
            "pages/overview.html",
            {**shell("overview"), "load_error": exc.correlation_id,
             "severity": severity, "status": status},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "pages/overview.html",
        {**shell("overview"), "data": data, "severity": severity, "status": status,
         "caveat": VERDICT_CAVEAT},
    )


@router.get("/incidents", response_class=HTMLResponse)
def incidents(
    request: Request,
    severity: str = Query(default="all"),
    status: str = Query(default="all"),
) -> HTMLResponse:
    try:
        data = deps.get_overview(severity=severity, status=status)
    except MockOperationsError as exc:
        return templates.TemplateResponse(
            request,
            "pages/incidents.html",
            {**shell("incidents"), "load_error": exc.correlation_id,
             "severity": severity, "status": status},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "pages/incidents.html",
        {**shell("incidents"), "incidents": data.incidents,
         "severity": severity, "status": status},
    )


@router.get("/incidents/{incident_id}/export", include_in_schema=False)
def incident_export(incident_id: str) -> Response:
    try:
        detail = deps.get_incident(incident_id)
    except UnknownIncidentError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except MockOperationsError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc),
                                                      "correlation_id": exc.correlation_id})
    payload = detail.model_dump()
    payload["_demo_notice"] = "DEMO DATA — replaceable mock case file."
    return JSONResponse(content=payload)


@router.post("/incidents/{incident_id}/actions", include_in_schema=False)
def incident_action(request: Request, incident_id: str, action: str = Query(default="note"),
                    note: str = Query(default="")) -> Response:
    try:
        entry = deps.record_incident_action(incident_id, action, note=note)
    except UnknownIncidentError:
        return templates.TemplateResponse(
            request,
            "pages/incidents.html",
            {**shell("incidents"), "incidents": deps.get_overview().incidents,
             "severity": "all", "status": "all",
             "not_found": incident_id.strip()},
            status_code=404,
        )
    _ = entry
    flag = "accepted" if action == "accept" else "noted"
    return RedirectResponse(url=f"/incidents/{incident_id.strip().upper()}?notice={flag}",
                            status_code=303)


@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
def incident_detail(
    request: Request,
    incident_id: str,
    notice: str = Query(default=""),
) -> HTMLResponse:
    try:
        detail = deps.get_incident(incident_id)
    except UnknownIncidentError:
        return templates.TemplateResponse(
            request,
            "pages/incidents.html",
            {**shell("incidents"), "incidents": deps.get_overview().incidents,
             "severity": "all", "status": "all",
             "not_found": incident_id.strip()},
            status_code=404,
        )
    except MockOperationsError as exc:
        return templates.TemplateResponse(
            request,
            "pages/incidents.html",
            {**shell("incidents"), "incidents": [],
             "severity": "all", "status": "all",
             "load_error": exc.correlation_id},
            status_code=502,
        )
    flash = None
    if notice == "noted":
        flash = Notice(kind="info", text="Note recorded in this demo session — no backend write.")
    elif notice == "accepted":
        flash = Notice(kind="info", text="Case accepted for investigation in this demo — findings preserved.")
    return templates.TemplateResponse(
        request,
        "pages/incident_detail.html",
        {**shell("incidents"), "d": detail, "flash": flash, "caveat": VERDICT_CAVEAT},
    )
