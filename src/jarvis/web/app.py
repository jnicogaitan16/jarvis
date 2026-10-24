"""JARVIS Web — FastAPI server con dashboard y API REST."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jarvis import __version__
from jarvis.web.api import router as api_router
from jarvis.web.pages import router as pages_router

_BASE = Path(__file__).parent

app = FastAPI(
    title="JARVIS",
    description="Plataforma personal de IA híbrida",
    version=__version__,
)

templates = Jinja2Templates(directory=str(_BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(api_router, prefix="/api/v1")
app.include_router(pages_router)
