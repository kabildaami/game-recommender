"""Pydantic request/response models for the GameGem web API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    reply: str
    route: int
    session_id: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]


class StatsResponse(BaseModel):
    session_id: str
    stats: Dict[str, Any]


class ClearResponse(BaseModel):
    session_id: str
    cleared: bool
