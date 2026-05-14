from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    approvals,
    attacks,
    campaigns,
    observability,
    regression,
    taxonomy,
    verdicts,
    vulnerabilities,
)
from api.slack_handler import router as slack_router
from api.websocket import router as ws_router

ALLOWED_ORIGINS = ["https://agentforge-adversarial-ai-security-8hlh.onrender.com"]

app = FastAPI(title="AgentForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


@app.get("/")
async def health_check() -> dict:
    return {"status": "ok", "service": "AgentForge API"}

app.include_router(campaigns.router, prefix="/api/campaigns")
app.include_router(attacks.router, prefix="/api/attacks")
app.include_router(verdicts.router, prefix="/api/verdicts")
app.include_router(vulnerabilities.router, prefix="/api/vulnerabilities")
app.include_router(regression.router, prefix="/api/regression")
app.include_router(taxonomy.router, prefix="/api/taxonomy")
app.include_router(observability.router, prefix="/api/observability")
app.include_router(approvals.router, prefix="/api/approvals")
app.include_router(slack_router)
app.include_router(ws_router)
