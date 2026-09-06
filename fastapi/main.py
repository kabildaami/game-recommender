"""GameGem FastAPI application.

Serves the existing frontend folder and exposes both streaming and normal
chat endpoints backed by one stateful GameChatResponder per browser session.
"""
from __future__ import annotations

import logging
from pathlib import Path
import sys

# IMPORTANT: put the project root before this local `fastapi/` directory so
# responder.py imports the RAG project's root config.py, prompts.py, etc.
API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from api_settings import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    HOST,
    PORT,
    SESSION_TTL_MINUTES,
)
from schemas import ChatRequest, ChatResponse, ClearResponse, HistoryResponse, StatsResponse
from session_manager import SessionManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gamegem.api")

FRONTEND_DIR = PROJECT_ROOT / "frontend"
if not FRONTEND_DIR.exists():
    raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR}")

app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-GameGem-Session-ID"],
)

# Keep the frontend's existing relative paths working without forcing you to
# reorganize it into Jinja templates/static directories.
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

sessions = SessionManager(ttl_minutes=SESSION_TTL_MINUTES)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "GameGem API",
        "active_sessions": sessions.active_count(),
        "streaming": True,
    }


@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """Stream one GameGem reply as plain UTF-8 text chunks.

    The browser uses fetch() + ReadableStream.getReader() to paint these chunks
    directly into the assistant message bubble as Groq produces them.
    """
    session_id, record = sessions.get_or_create(payload.session_id)

    def generate():
        # Prevent two overlapping turns from mutating the same conversation.
        with record.lock:
            record.touch()
            try:
                yield from record.responder.stream_chat(payload.message)
            except GeneratorExit:
                # Browser disconnected/cancelled; responder won't store a
                # partial assistant turn because stream_chat wasn't completed.
                raise
            except Exception:
                logger.exception("Streaming chat failed for session %s", session_id)
                yield "Sorry — GameGem had trouble generating that response. Please try again."
            finally:
                record.touch()

    # Forward Groq chunks immediately. Visual pacing is intentionally handled
    # by frontend/js/app.js so backend/model latency stays as low as possible.
    response = StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
    response.headers["X-GameGem-Session-ID"] = session_id
    response.headers["Cache-Control"] = "no-cache, no-transform"
    # Helpful when deployed behind nginx/reverse proxies that buffer streams.
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.post("/api/chat", response_model=ChatResponse)
def chat_complete(payload: ChatRequest) -> ChatResponse:
    """Non-streaming fallback/debug endpoint."""
    session_id, record = sessions.get_or_create(payload.session_id)
    with record.lock:
        try:
            reply, route = record.responder.respond(payload.message)
        except Exception as exc:
            logger.exception("Chat failed for session %s", session_id)
            raise HTTPException(status_code=500, detail="GameGem response generation failed") from exc
        finally:
            record.touch()

    return ChatResponse(reply=reply, route=route, session_id=session_id)


@app.get("/api/sessions/{session_id}/history", response_model=HistoryResponse)
def session_history(session_id: str) -> HistoryResponse:
    record = sessions.get_existing(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    with record.lock:
        return HistoryResponse(session_id=session_id, messages=record.responder.get_history())


@app.get("/api/sessions/{session_id}/stats", response_model=StatsResponse)
def session_stats(session_id: str) -> StatsResponse:
    record = sessions.get_existing(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    with record.lock:
        return StatsResponse(session_id=session_id, stats=record.responder.get_stats())


@app.delete("/api/sessions/{session_id}", response_model=ClearResponse)
def clear_session(session_id: str) -> ClearResponse:
    record = sessions.get_existing(session_id)
    if record is None:
        return ClearResponse(session_id=session_id, cleared=False)
    with record.lock:
        record.responder.clear_history()
        record.touch()
    return ClearResponse(session_id=session_id, cleared=True)


if __name__ == "__main__":
    import uvicorn

    # For reload during development, prefer:
    # uvicorn --app-dir fastapi main:app --reload
    uvicorn.run(app, host=HOST, port=PORT)
