"""HTTP entry points with per-assessment models and independent authorization."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .connections import (ConnectionConfigurationError, PROVIDER_KEY_HEADER,
                          make_connection, provider_options)
from .gateway import HttpGateway
from .llm_planner import PlannerUnavailable
from .models import AgentRequest, AgentResponse, FinalAction, ModelSettings
from .runtime import AgentRuntime
from .adversarial_cases import catalog, find_case, unavailable_reason

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(title="AgentSentry Target Agent")


def make_planner():
    """Preserve the existing factory for environment-based callers and tests."""
    return make_connection()[0]


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError):
    # Never echo rejected credentials accidentally supplied in the JSON body.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error["loc"]), "type": error["type"], "msg": error["msg"]}
        for error in exc.errors()
    ]})


def connection(selection: ModelSettings | None, request: Request):
    try:
        return make_connection(selection, request.headers.get(PROVIDER_KEY_HEADER))
    except ConnectionConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.get("/health")
def health():
    """API liveness; the explicit connection check exercises a model."""
    return {"status": "ok"}


@app.get("/model/providers")
def providers():
    """Return non-secret defaults before any provider key has been entered."""
    return {"providers": provider_options()}


@app.get("/agent/scenarios")
def scenarios():
    """Expose Ying's exact prompts and review criteria; execute nothing."""
    return catalog()


@app.post("/model/check")
async def check_model(selection: ModelSettings, http_request: Request):
    """One small model request, with no gateway call or recorded finding."""
    planner, settings = connection(selection, http_request)
    probe = AgentRequest(scan_id="CONNECTION-CHECK", test_id="CONNECTION-CHECK",
                         user="connection-check", role="employee",
                         message="Connection check. Reply with a final message saying Ready. Do not use tools.")
    try:
        action = await planner.next_action(probe, [])
    except PlannerUnavailable:
        raise HTTPException(status_code=502, detail="Model check failed. Check the key, model support, service availability, and quota.") from None
    if settings.provider != "rule" and not isinstance(action, FinalAction):
        raise HTTPException(status_code=502, detail="The model did not return the expected final action.")
    return {"status": "ok", "model_settings": settings.model_dump()}


@app.post("/agent/message", response_model=AgentResponse)
async def message(request: AgentRequest, http_request: Request):
    case = find_case(request.test_id)
    if case and (reason := unavailable_reason(case)):
        raise HTTPException(status_code=409, detail="Not run - " + reason)
    # A fresh planner prevents provider/key changes leaking into another run.
    planner, settings = connection(request.model_settings, http_request)
    if case and (reason := unavailable_reason(case, settings.provider)):
        raise HTTPException(status_code=409, detail="Not run - " + reason)
    response = await AgentRuntime(planner, HttpGateway()).run(request)
    return response.model_copy(update={"model_settings": settings})
