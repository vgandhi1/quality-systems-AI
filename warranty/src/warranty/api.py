"""
Warranty adjudication FastAPI service.

Endpoints:
  GET  /                    — redirect to /docs
  GET  /health              — service status
  POST /adjudicate/dry-run  — deterministic pipeline (no LLM)
  POST /escalate/handoff    — build QualityMind RCA payload from claim state
  POST /escalate/execute    — handoff + live POST to QualityMind
"""

from __future__ import annotations

import hmac
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from warranty import __version__
from warranty.claim_tools import ClaimStore
from warranty.config import (
    WORKSPACE_DIR,
    auth_required,
    get_api_host,
    get_api_key,
    get_api_port,
    get_cors_origins,
    get_environment,
    validate_api_config,
)
from warranty.handoff import build_escalation
from warranty.orchestrator import run_dry_pipeline
from warranty.qualitymind_client import QualityMindClientError, execute_escalation
from warranty.schema import AdjudicateResponse, DryRunRequest, RcaEscalation, RcaEscalationResponse

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PUBLIC_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/"})


def create_app() -> FastAPI:
    application = FastAPI(
        title="Warranty Adjudication",
        version=__version__,
        description="Dealership warranty payment adjudication agent POC",
    )

    cors_origins = get_cors_origins()
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    @application.middleware("http")
    async def api_key_guard(request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs"):
            return await call_next(request)

        api_key = get_api_key()
        if not api_key and not auth_required():
            return await call_next(request)

        if not api_key:
            return JSONResponse(
                status_code=503,
                content={"detail": "API authentication is not configured"},
            )

        provided = request.headers.get("X-API-Key")
        if not provided or not hmac.compare_digest(provided, api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
        return await call_next(request)

    @application.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "environment": get_environment(),
            "auth_required": auth_required(),
        }

    @application.post("/adjudicate/dry-run", response_model=AdjudicateResponse)
    def adjudicate_dry_run(body: DryRunRequest) -> AdjudicateResponse:
        with tempfile.TemporaryDirectory() as tmp:
            state = run_dry_pipeline(Path(tmp), body.scenario)
        escalation = build_escalation(state)
        return AdjudicateResponse(claim_state=state, escalation=escalation)

    @application.post("/escalate/handoff", response_model=RcaEscalation)
    def escalate_handoff(claim_state: dict) -> RcaEscalation:
        escalation = build_escalation(claim_state)
        if escalation is None:
            raise HTTPException(
                status_code=400,
                detail="Claim did not route to HUMAN_REVIEW or state is incomplete",
            )
        return escalation

    @application.post("/escalate/execute", response_model=RcaEscalationResponse)
    def escalate_execute(claim_state: dict) -> RcaEscalationResponse:
        escalation = build_escalation(claim_state)
        if escalation is None:
            raise HTTPException(
                status_code=400,
                detail="Claim did not route to HUMAN_REVIEW or state is incomplete",
            )
        try:
            qm_response = execute_escalation(escalation)
        except QualityMindClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RcaEscalationResponse(**escalation.model_dump(), qualitymind_response=qm_response)

    @application.get("/claim-state")
    def read_claim_state() -> dict:
        store = ClaimStore(WORKSPACE_DIR)
        data = json.loads(store.read_claim_state())
        if data.get("status") == "NOT_INITIALIZED":
            raise HTTPException(status_code=404, detail="Claim state not initialized")
        return data

    return application


app = create_app()


def run() -> None:
    validate_api_config()
    import uvicorn

    uvicorn.run(
        create_app(),
        host=get_api_host(),
        port=get_api_port(),
        reload=False,
    )
