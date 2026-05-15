from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=_cors_headers(request),
    )


@app.get("/api/health")
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

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def spa_root() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str) -> FileResponse:
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = FRONTEND_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
