# GameGem FastAPI bridge

This folder connects the existing GameGem browser UI to `responder.py`.

## Why there is no `__init__.py`

The folder is named `fastapi`, the same name as the installed Python package.
Keeping this folder as a plain directory avoids unnecessarily turning it into a
local package named `fastapi`.

## Endpoints

- `GET /` — serves `../frontend/index.html`
- `GET /api/health` — API health/status
- `POST /api/chat/stream` — **streaming** GameGem response
- `POST /api/chat` — complete JSON response (fallback/debug)
- `GET /api/sessions/{id}/history` — inspect conversation history
- `GET /api/sessions/{id}/stats` — inspect responder stats
- `DELETE /api/sessions/{id}` — clear conversation memory

## Streaming request

```json
{
  "message": "Recommend a cheap co-op game on PS5",
  "session_id": null
}
```

The response body is streamed as plain UTF-8 text. The response header
`X-GameGem-Session-ID` contains the session ID. The frontend saves it to
`localStorage` and sends it with the next turn.

## Start

From the project root:

```bash
pip install -r fastapi/requirements.txt
uvicorn --app-dir fastapi main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Do **not** open `frontend/index.html` directly with `file://`; use the FastAPI
URL so the frontend and chat API share the same origin.

## Session model

The session manager is intentionally in-memory for this stage of the project.
Each browser session receives one `GameChatResponder`, so multi-turn history is
kept correctly. A server restart clears sessions. For multi-worker production,
move session history to Redis/PostgreSQL rather than relying on process memory.
