"""Settings used only by the GameGem FastAPI web layer.

This module is intentionally NOT named config.py because the RAG project
already has a root config.py imported by responder.py.
"""
from __future__ import annotations

import os

APP_TITLE = os.getenv("GAMEGEM_API_TITLE", "GameGem API")
APP_DESCRIPTION = os.getenv(
    "GAMEGEM_API_DESCRIPTION",
    "FastAPI bridge between the GameGem frontend and the Groq/RAG responder.",
)
HOST = os.getenv("GAMEGEM_HOST", "127.0.0.1")
PORT = int(os.getenv("GAMEGEM_PORT", "8000"))
SESSION_TTL_MINUTES = int(os.getenv("GAMEGEM_SESSION_TTL_MINUTES", "120"))

DEFAULT_ORIGINS = (
    "http://127.0.0.1:8000,http://localhost:8000,"
    "http://127.0.0.1:5500,http://localhost:5500,"
    "http://127.0.0.1:5173,http://localhost:5173"
)
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv("GAMEGEM_ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if item.strip()
]
