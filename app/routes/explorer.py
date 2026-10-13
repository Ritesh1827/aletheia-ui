"""Provenance Block Explorer routes. Static paths before param paths."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.routes import session
from app.services import deps
from app.services.mock_explorer import ExplorerBackendError, UnknownRecordError

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class ExplorerNotice(BaseModel):
    kind: str
    text: str


@router.get("/explorer", response_class=HTMLResponse)
def explorer_home(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    mode: str = Query(default="live"),
) -> HTMLResponse:
    query = q.strip()
    if query:
        hits = deps.search_explorer(query)
        if len(hits) == 1:
            return templates.TemplateResponse(
                request,
                "pages/explorer_search.html",
                {**session.shell(request, "explorer"), "q": q, "hits": hits, "single": True},
            )
        try:
            data = deps.get_explorer_overview(page=page, mode=mode)
        except ExplorerBackendError as exc:
            return templates.TemplateResponse(
                request,
                "pages/explorer.html",
                {**session.shell(request, "explorer"), "load_error": exc.correlation_id,
                 "q": q, "hits": hits, "page": page, "mode": mode},
                status_code=502,
            )
        data.query = q
        data.hits = hits
        return templates.TemplateResponse(
            request,
            "pages/explorer.html",
            {**session.shell(request, "explorer"), "data": data, "q": q, "page": page, "mode": mode},
        )
    try:
        data = deps.get_explorer_overview(page=page, mode=mode)
    except ExplorerBackendError as exc:
        return templates.TemplateResponse(
            request,
            "pages/explorer.html",
            {**session.shell(request, "explorer"), "load_error": exc.correlation_id,
             "q": q, "page": page, "mode": mode},
            status_code=502,
        )
    return templates.TemplateResponse(
        request,
        "pages/explorer.html",
        {**session.shell(request, "explorer"), "data": data, "q": q, "page": page, "mode": mode},
    )


@router.get("/explorer/search", response_class=HTMLResponse, include_in_schema=False)
def explorer_search(request: Request, q: str = Query(default="")) -> HTMLResponse:
    query = q.strip()
    hits = deps.search_explorer(query) if query else []
    if len(hits) == 1:
        return templates.TemplateResponse(
            request,
            "pages/explorer_search.html",
            {**session.shell(request, "explorer"), "q": q, "hits": hits, "single": True},
        )
    return templates.TemplateResponse(
        request,
        "pages/explorer_search.html",
        {**session.shell(request, "explorer"), "q": q, "hits": hits, "single": False},
    )


@router.get("/explorer/block/{block_id}", response_class=HTMLResponse)
def explorer_block(request: Request, block_id: str) -> HTMLResponse:
    try:
        block = deps.get_explorer_block(block_id)
    except UnknownRecordError:
        return templates.TemplateResponse(
            request,
            "pages/explorer_search.html",
            {**session.shell(request, "explorer"), "q": block_id.strip(), "hits": [],
             "single": False, "not_found": block_id.strip()},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "pages/explorer_block.html",
        {**session.shell(request, "explorer"), "block": block},
    )


@router.get("/explorer/tx/{tx_hash}/proof", include_in_schema=False)
def explorer_proof_json(tx_hash: str, verify: str = Query(default="0")) -> Response:
    try:
        proof = deps.get_merkle_proof(tx_hash, verify=(verify == "1"))
    except UnknownRecordError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    payload = proof.model_dump()
    payload["_demo_notice"] = "DEMO DATA — computed locally against mock fixtures."
    return JSONResponse(content=payload)


@router.get("/explorer/tx/{tx_hash}", response_class=HTMLResponse)
def explorer_tx(
    request: Request,
    tx_hash: str,
    verify: str = Query(default="0"),
    notice: str = Query(default=""),
) -> HTMLResponse:
    try:
        detail = deps.get_explorer_tx(tx_hash)
        proof = deps.get_merkle_proof(tx_hash, verify=(verify == "1"))
    except UnknownRecordError:
        return templates.TemplateResponse(
            request,
            "pages/explorer_search.html",
            {**session.shell(request, "explorer"), "q": tx_hash.strip(), "hits": [],
             "single": False, "not_found": tx_hash.strip()},
            status_code=404,
        )
    flash = None
    if verify == "1":
        if proof.status == "PROOF VALID":
            flash = ExplorerNotice(kind="good", text="Verification ran: computed root matches the anchored root.")
        elif proof.status == "PROOF INVALID":
            flash = ExplorerNotice(kind="error", text="Verification ran: computed root differs — treat inclusion as unproven.")
        else:
            flash = ExplorerNotice(kind="info", text="Nothing to verify against for this transaction yet.")
    elif notice == "verified":
        flash = ExplorerNotice(kind="info", text="Proof panel updated.")
    return templates.TemplateResponse(
        request,
        "pages/explorer_tx.html",
        {**session.shell(request, "explorer"), "tx": detail, "proof": proof,
         "verifying": verify == "1", "flash": flash},
    )


@router.get("/explorer/address/{address}", response_class=HTMLResponse)
def explorer_address(request: Request, address: str) -> HTMLResponse:
    try:
        info = deps.get_explorer_address(address)
    except UnknownRecordError:
        return templates.TemplateResponse(
            request,
            "pages/explorer_search.html",
            {**session.shell(request, "explorer"), "q": address.strip(), "hits": [],
             "single": False, "not_found": address.strip()},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "pages/explorer_address.html",
        {**session.shell(request, "explorer"), "info": info},
    )
