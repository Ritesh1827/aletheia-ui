"""Verify routes: search + verdict detail."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.models.verify import VERDICT_CAVEAT, VERDICT_LABELS
from app.routes import session
from app.services import deps
from app.services.mock_verify import MockBackendError, UnknownSerialError
from app.services.scan_parse import parse_scan_payload

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/verify", status_code=307)


@router.get("/verify", response_class=HTMLResponse)
def verify_search(
    request: Request,
    q: str = Query(default="", description="Serial or QR payload"),
    error: str = Query(default=""),
) -> Response:
    query = q.strip()
    if query:
        parsed = parse_scan_payload(query)
        lookup = parsed.serial if parsed.status == "serial" else query
        try:
            verdict = deps.get_verification(lookup)
        except UnknownSerialError:
            return templates.TemplateResponse(
                request,
                "pages/verify_search.html",
                {**session.shell(request, "verify"), "q": q, "not_found": lookup,
                 "scan_note": parsed.explanation if parsed.status == "ambiguous" else ""},
            )
        except MockBackendError as exc:
            return templates.TemplateResponse(
                request,
                "pages/verify_search.html",
                {**session.shell(request, "verify"), "q": q, "backend_error": exc.correlation_id},
            )
        return RedirectResponse(url=f"/verify/{verdict.serial}", status_code=303)
    return templates.TemplateResponse(
        request,
        "pages/verify_search.html",
        {**session.shell(request, "verify"), "q": q, "form_error": error},
    )


@router.get("/verify/{serial}", response_class=HTMLResponse)
def verify_detail(request: Request, serial: str) -> HTMLResponse:
    try:
        verdict = deps.get_verification(serial)
    except UnknownSerialError:
        return templates.TemplateResponse(
            request,
            "pages/verify_search.html",
            {**session.shell(request, "verify"), "q": serial, "not_found": serial.strip()},
            status_code=404,
        )
    except MockBackendError as exc:
        return templates.TemplateResponse(
            request,
            "pages/verify_search.html",
            {**session.shell(request, "verify"), "q": serial, "backend_error": exc.correlation_id},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "pages/verify_detail.html",
        {
            **session.shell(request, "verify"),
            "v": verdict,
            "verdict_label": VERDICT_LABELS[verdict.verdict],
            "caveat": VERDICT_CAVEAT,
        },
    )


@router.get("/verify/{serial}/bundle", include_in_schema=False)
def verify_bundle(serial: str) -> Response:
    try:
        verdict = deps.get_verification(serial)
    except (UnknownSerialError, MockBackendError) as exc:
        status = 404 if isinstance(exc, UnknownSerialError) else 502
        return JSONResponse(
            status_code=status,
            content={"error": str(exc), "serial": serial.strip(),
                     "_demo_notice": "DEMO DATA — mock failure, never a successful verification."},
        )
    payload = verdict.model_dump()
    payload["_demo_notice"] = "DEMO DATA — replaceable mock proof bundle."
    return JSONResponse(content=payload)
