from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="AgentForge API", version="1.0.0")


@app.get("/")
async def health_check() -> dict:
    return {"status": "ok", "service": "AgentForge API"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agentforge-adversarial-ai-security-8hlh.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
