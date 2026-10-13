"""Red-Team Lab routes. Demo-gated scenario console; static paths first."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import config
from app.routes import session
from app.services import deps
from app.services.mock_redteam import (
    SCENARIO_IDS,
    InvalidScenarioInputError,
    UnknownScenarioError,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class LabNotice(BaseModel):
    kind: str
    text: str


def shell(active: str) -> dict[str, object]:
    return {
        "demo": config.is_demo(),
        "chain_label": config.chain_label(),
        "active": active,
    }


def _guard(request: Request) -> HTMLResponse | None:
    """Demo auth guard: lab runs only in mock/demo mode.

    There is no real RBAC yet — the shell account is a read-only demo
    identity, so execution is gated on demo mode and labelled as such.
    """
    if not config.is_demo():
        return templates.TemplateResponse(
            request,
            "pages/redteam.html",
            {**session.shell(request, "redteam"), "forbidden": True},
            status_code=403,
        )
    return None


@router.get("/red-team", response_class=HTMLResponse)
def redteam_home(
    request: Request,
    scenario: str = Query(default=""),
    ran: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    blocked = _guard(request)
    if blocked is not None:
        return blocked
    run_state = {sid: True for sid in ran.split(",") if sid in SCENARIO_IDS} if ran else {}
    lab = deps.get_redteam_lab(run_state)
    selected = scenario.strip().lower() if scenario.strip().lower() in SCENARIO_IDS else ""
    fields = lab.fields.get(selected, []) if selected else []
    return templates.TemplateResponse(
        request,
        "pages/redteam.html",
        {**session.shell(request, "redteam"), "lab": lab, "selected": selected,
         "fields": fields, "ran": ran, "form_error": error},
    )


@router.get("/red-team/{scenario_id}", response_class=HTMLResponse)
def redteam_scenario(
    request: Request,
    scenario_id: str,
    ran: str = Query(default=""),
    result: str = Query(default=""),
    error: str = Query(default=""),
) -> HTMLResponse:
    blocked = _guard(request)
    if blocked is not None:
        return blocked
    key = scenario_id.strip().lower()
    if key not in SCENARIO_IDS:
        run_state = {sid: True for sid in ran.split(",") if sid in SCENARIO_IDS} if ran else {}
        lab = deps.get_redteam_lab(run_state)
        return templates.TemplateResponse(
            request,
            "pages/redteam.html",
            {**session.shell(request, "redteam"), "lab": lab, "selected": "", "fields": [],
             "ran": ran, "form_error": f"Unknown scenario: {scenario_id.strip()}."},
            status_code=404,
        )
    run_state = {sid: True for sid in ran.split(",") if sid in SCENARIO_IDS} if ran else {}
    lab = deps.get_redteam_lab(run_state)
    meta = next(s for s in lab.scenarios if s.id == key)
    fields = lab.fields.get(key, [])
    last_result = None
    if result == "1":
        try:
            last_result = deps.run_redteam_scenario(key, dict(request.query_params))
        except (UnknownScenarioError, InvalidScenarioInputError):
            last_result = None
    return templates.TemplateResponse(
        request,
        "pages/redteam_result.html",
        {**session.shell(request, "redteam"), "lab": lab, "meta": meta, "fields": fields,
         "ran": ran, "result": last_result, "form_error": error},
    )


@router.post("/red-team/{scenario_id}/run", include_in_schema=False)
async def redteam_run(request: Request, scenario_id: str) -> Response:
    blocked = _guard(request)
    if blocked is not None:
        return blocked
    denied = session.guard(request, "redteam:run", scenario_id.strip().lower(),
                           active="redteam")
    if denied is not None:
        return denied
    key = scenario_id.strip().lower()
    if key not in SCENARIO_IDS:
        return templates.TemplateResponse(
            request,
            "pages/redteam.html",
            {**session.shell(request, "redteam"), "lab": deps.get_redteam_lab(),
             "selected": "", "fields": [], "ran": "",
             "form_error": f"Unknown scenario: {scenario_id.strip()}."},
            status_code=404,
        )
    form = await request.form()
    inputs = {k: str(v) for k, v in form.items() if k != "ran"}
    ran = str(form.get("ran", ""))
    try:
        result = deps.run_redteam_scenario(key, inputs)
    except InvalidScenarioInputError as exc:
        deps.audit_record(session.actor_id(request), "redteam:run", key,
                          "rejected", {"reason": "invalid-input"})
        lab = deps.get_redteam_lab()
        meta = next(s for s in lab.scenarios if s.id == key)
        return templates.TemplateResponse(
            request,
            "pages/redteam_result.html",
            {**session.shell(request, "redteam"), "lab": lab, "meta": meta,
             "fields": lab.fields.get(key, []), "ran": ran,
             "result": None, "form_error": exc.detail},
            status_code=422,
        )
    _ = result
    deps.audit_record(session.actor_id(request), "redteam:run", key, "allowed", {})
    seen = [s for s in ran.split(",") if s in SCENARIO_IDS] if ran else []
    if key not in seen:
        seen.append(key)
    params = "&".join(f"{k}={v}" for k, v in inputs.items())
    tail = f"&{params}" if params else ""
    return RedirectResponse(
        url=f"/red-team/{key}?ran={','.join(seen)}&result=1{tail}",
        status_code=303,
    )


@router.get("/red-team/{scenario_id}/result", include_in_schema=False)
def redteam_result_json(request: Request, scenario_id: str) -> Response:
    blocked_payload = not config.is_demo()
    if blocked_payload:
        return JSONResponse(status_code=403, content={"error": "Red-Team Lab is demo-only."})
    denied = session.guard(request, "redteam:run", scenario_id.strip().lower(),
                           active="redteam")
    if denied is not None:
        return JSONResponse(status_code=403, content={
            "error": "Role lacks permission 'redteam:run'.",
            "_demo_notice": "DEMO DATA — backend denial, never a result.",
        })
    try:
        result = deps.run_redteam_scenario(scenario_id.strip().lower(), {})
    except UnknownScenarioError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except InvalidScenarioInputError as exc:
        return JSONResponse(status_code=422, content={"error": exc.detail})
    payload = result.model_dump()
    payload["_demo_notice"] = "DEMO DATA — simulated scenario result."
    return JSONResponse(content=payload)
