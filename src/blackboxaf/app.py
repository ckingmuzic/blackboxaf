"""BlackBoxAF - FastAPI application entry point."""

from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.ingest import router as ingest_router
from .api.patterns import router as patterns_router
from .config import FRONTEND_DIR
from .db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="BlackBoxAF",
    description="Salesforce metadata pattern extraction and reuse tool",
    version="0.1.0",
)

# ── Security hardening ──

# Host header validation: blocks DNS rebinding attacks
# (malicious sites tricking your browser into sending requests to localhost)
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "localhost:8000", "127.0.0.1:8000"}


@app.middleware("http")
async def validate_host_header(request: Request, call_next):
    host = request.headers.get("host", "")
    if host not in _ALLOWED_HOSTS:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


# CORS: only allow requests from our own frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Register API routes
app.include_router(ingest_router)
app.include_router(patterns_router)

# Serve static frontend files
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logging.getLogger("blackboxaf").info("BlackBoxAF started. Database initialized.")


@app.get("/")
async def serve_index():
    """Serve the main frontend page."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/detail")
async def serve_detail():
    """Serve the pattern detail page."""
    return FileResponse(str(FRONTEND_DIR / "detail.html"))


def main():
    """Run the BlackBoxAF server."""
    import sys
    import uvicorn

    print(r"""
    ____  __           __   ____                ___    ______
   / __ )/ /___ ______/ /__/ __ )____  _  __   /   |  / ____/
  / __  / / __ `/ ___/ //_/ __  / __ \| |/_/  / /| | / /_
 / /_/ / / /_/ / /__/ ,< / /_/ / /_/ />  <   / ___ |/ __/
/_____/_/\__,_/\___/_/|_/_____/\____/_/|_|  /_/  |_/_/

    Salesforce Pattern Extraction & Reuse Tool
    """)
    print("  Starting server at http://localhost:8000")
    print("  Press Ctrl+C to stop\n")

    # Open browser automatically
    webbrowser.open("http://localhost:8000")

    if getattr(sys, "frozen", False):
        # PyInstaller .exe: pass the app object directly
        # (string imports don't work in frozen mode)
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )
    else:
        # Development: use string import for auto-reload support
        uvicorn.run(
            "blackboxaf.app:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info",
        )


if __name__ == "__main__":
    main()
