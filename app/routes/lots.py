"""Lots & Recall routes (M5). Static paths before param paths."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import config
from app.models.verify import VERDICT_CAVEAT
from app.routes import session as sess
from app.services import deps
from app.services.mock_lots import LotsBackendError, UnknownLotError

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class LotsNotice(BaseModel):
    kind: str
    text: str


def shell(active: str) -> dict[str, object]:
    return {
        "demo": config.is_demo(),
        "chain_label": config.chain_label(),
        "active": active,
    }


@router.get("/lots", response_class=HTMLResponse)
def lots_home(
    request: Request,
    q: str = Query(default=""),
    freeze: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    fail: str = Query(default=""),
) -> HTMLResponse:
    try:
        lots = deps.list_lots(query=q, freeze=freeze, fail=(fail == "1"))
    except LotsBackendError as exc:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "load_error": exc.correlation_id,
             "q": q, "freeze": freeze, "page": 1, "pages": 1, "lots": []},
            status_code=502,
        )
    per_page = 10
    pages = max(1, (len(lots) + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    window = lots[(page - 1) * per_page: page * per_page]
    return templates.TemplateResponse(
        request,
        "pages/lots.html",
        {**shell("lots"), "lots": window, "total": len(lots),
         "q": q, "freeze": freeze, "page": page, "pages": pages},
    )


@router.get("/lots/{lot_id}/blast-radius", response_class=HTMLResponse)
def lot_blast_radius(request: Request, lot_id: str) -> HTMLResponse:
    try:
        detail = deps.get_lot(lot_id)
        blast = deps.get_blast_radius(lot_id)
    except UnknownLotError:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "lots": deps.list_lots(), "total": 2,
             "q": "", "freeze": "all", "page": 1, "pages": 1,
             "not_found": lot_id.strip()},
            status_code=404,
        )
    except LotsBackendError as exc:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "load_error": exc.correlation_id,
             "q": "", "freeze": "all", "page": 1, "pages": 1, "lots": []},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "pages/lot_blast.html",
        {**shell("lots"), "lot": detail, "blast": blast, "caveat": VERDICT_CAVEAT},
    )


@router.post("/lots/{lot_id}/freeze", include_in_schema=False)
async def lot_freeze(request: Request, lot_id: str) -> Response:
    role = sess.current_role(request)
    if role != 'operator':
        return templates.TemplateResponse(
            request,
            'pages/lot_detail.html',
            {**shell('lots'), 'lot': deps.get_lot(lot_id), 'blast': None,
             'caveat': VERDICT_CAVEAT, 'can_act': False,
             'form_error': 'Operator role required — switch role to act.'},
            status_code=403,
        )
    form = await request.form()
    reason = str(form.get("reason", ""))[:500]
    confirmed = str(form.get("confirm", ""))[:128]
    if confirmed != lot_id.strip().upper():
        return templates.TemplateResponse(
            request,
            "pages/lot_detail.html",
            {**shell("lots"), "lot": deps.get_lot(lot_id), "blast": None,
             "caveat": VERDICT_CAVEAT,
             "form_error": "Confirmation did not match the lot ID — no action taken."},
            status_code=422,
        )
    try:
        entry = deps.freeze_lot(lot_id, reason, role)
    except UnknownLotError:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "lots": deps.list_lots(), "total": 2,
             "q": "", "freeze": "all", "page": 1, "pages": 1,
             "not_found": lot_id.strip()},
            status_code=404,
        )
    _ = entry
    return Response(status_code=303, headers={"Location": f"/lots/{lot_id.strip().upper()}?notice=frozen"})


@router.post("/lots/{lot_id}/recall", include_in_schema=False)
async def lot_recall(request: Request, lot_id: str) -> Response:
    role = sess.current_role(request)
    if role != 'operator':
        return templates.TemplateResponse(
            request,
            'pages/lot_detail.html',
            {**shell('lots'), 'lot': deps.get_lot(lot_id), 'blast': None,
             'caveat': VERDICT_CAVEAT, 'can_act': False,
             'form_error': 'Operator role required — switch role to act.'},
            status_code=403,
        )
    form = await request.form()
    reason = str(form.get("reason", ""))[:500]
    confirmed = str(form.get("confirm", ""))[:128]
    if confirmed != lot_id.strip().upper():
        return templates.TemplateResponse(
            request,
            "pages/lot_detail.html",
            {**shell("lots"), "lot": deps.get_lot(lot_id), "blast": None,
             "caveat": VERDICT_CAVEAT,
             "form_error": "Confirmation did not match the lot ID — no action taken."},
            status_code=422,
        )
    try:
        entry = deps.recall_lot(lot_id, reason, role)
    except UnknownLotError:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "lots": deps.list_lots(), "total": 2,
             "q": "", "freeze": "all", "page": 1, "pages": 1,
             "not_found": lot_id.strip()},
            status_code=404,
        )
    _ = entry
    return Response(status_code=303, headers={"Location": f"/lots/{lot_id.strip().upper()}?notice=recalled"})


@router.get("/lots/{lot_id}", response_class=HTMLResponse)
def lot_detail(
    request: Request,
    lot_id: str,
    notice: str = Query(default=""),
) -> HTMLResponse:
    try:
        detail = deps.get_lot(lot_id)
    except UnknownLotError:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "lots": deps.list_lots(), "total": 2,
             "q": "", "freeze": "all", "page": 1, "pages": 1,
             "not_found": lot_id.strip()},
            status_code=404,
        )
    except LotsBackendError as exc:
        return templates.TemplateResponse(
            request,
            "pages/lots.html",
            {**shell("lots"), "load_error": exc.correlation_id,
             "q": "", "freeze": "all", "page": 1, "pages": 1, "lots": []},
            status_code=502,
        )
    flash = None
    if notice == "frozen":
        flash = LotsNotice(kind="info", text="Freeze confirmed by the demo service — outbound transfer held (demo operation).")
    elif notice == "recalled":
        flash = LotsNotice(kind="info", text="Recall confirmed by the demo service — pull-stock queued and lot frozen (demo operation).")
    role = sess.current_role(request)
    return templates.TemplateResponse(
        request,
        "pages/lot_detail.html",
        {**shell("lots"), "lot": detail, "flash": flash,
         "caveat": VERDICT_CAVEAT, "form_error": "",
         "can_act": role == "operator", "role": role},
    )


@router.get("/lots/{lot_id}/audit", include_in_schema=False)
def lot_audit_json(lot_id: str) -> Response:
    try:
        detail = deps.get_lot(lot_id)
    except UnknownLotError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    payload = {"lot_id": detail.lot_id, "audit": [a.model_dump() for a in detail.audit]}
    payload["_demo_notice"] = "DEMO DATA — simulated lot action log."
    return JSONResponse(content=payload)
