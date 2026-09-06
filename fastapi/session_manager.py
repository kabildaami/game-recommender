"""In-memory browser session manager for stateful GameChatResponder objects.

The Groq API is stateless, but GameChatResponder is intentionally stateful.
One responder instance is therefore kept for each browser session ID.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import threading
import time
import uuid
from typing import Dict, Optional, Tuple

from responder import GameChatResponder


_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


@dataclass
class SessionRecord:
    responder: GameChatResponder
    lock: threading.RLock = field(default_factory=threading.RLock)
    last_seen: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_seen = time.time()


class SessionManager:
    def __init__(self, ttl_minutes: int = 120) -> None:
        self.ttl_seconds = max(5, ttl_minutes) * 60
        self._records: Dict[str, SessionRecord] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _valid_id(session_id: Optional[str]) -> bool:
        return bool(session_id and _SESSION_RE.fullmatch(session_id))

    def _cleanup_expired_locked(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        expired = [sid for sid, record in self._records.items() if record.last_seen < cutoff]
        for sid in expired:
            self._records.pop(sid, None)

    def get_or_create(self, requested_id: Optional[str] = None) -> Tuple[str, SessionRecord]:
        with self._lock:
            self._cleanup_expired_locked()
            session_id = requested_id if self._valid_id(requested_id) else None

            if session_id and session_id in self._records:
                record = self._records[session_id]
                record.touch()
                return session_id, record

            session_id = self._new_id()
            record = SessionRecord(responder=GameChatResponder())
            self._records[session_id] = record
            return session_id, record

    def get_existing(self, session_id: str) -> Optional[SessionRecord]:
        if not self._valid_id(session_id):
            return None
        with self._lock:
            self._cleanup_expired_locked()
            record = self._records.get(session_id)
            if record:
                record.touch()
            return record

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._records.pop(session_id, None) is not None

    def active_count(self) -> int:
        with self._lock:
            self._cleanup_expired_locked()
            return len(self._records)
