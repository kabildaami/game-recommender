"""Local tool registry used by the AI intent classifier and responder.

The classifier does not contain routing keywords or a hard-coded sentence map.
It reads these tool definitions and asks a language model to choose tool 1, 2,
or 3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ToolDefinition:
    number: int
    name: str
    briefing: str


_TOOLS: Tuple[ToolDefinition, ...] = (
    ToolDefinition(
        number=1,
        name="game_recommendation",
        briefing=(
            "Recommend games that match preferences or constraints such as genre, "
            "platform, budget, playtime, mood, multiplayer style, or similarity to another game."
        ),
    ),
    ToolDefinition(
        number=2,
        name="general_conversation",
        briefing=(
            "Handle greetings, thanks, casual conversation, or messages that do not require "
            "retrieving facts about a game or recommending games."
        ),
    ),
    ToolDefinition(
        number=3,
        name="game_details",
        briefing=(
            "Answer a question about a specific game or a game already discussed, including "
            "general information or a precise feature such as price, platform, playtime, "
            "genre, modes, difficulty, rating, release, franchise, or languages."
        ),
    ),
)

TOOLS_BY_NUMBER: Dict[int, ToolDefinition] = {tool.number: tool for tool in _TOOLS}


def get_registered_tools() -> Tuple[ToolDefinition, ...]:
    """Return the immutable set of registered tools."""
    return _TOOLS


def get_classifier_briefing() -> str:
    """Compact registry text injected into the classifier prompt."""
    return "\n".join(
        f"{tool.number}={tool.name}: {tool.briefing}" for tool in _TOOLS
    )


def get_tool(number: int) -> ToolDefinition:
    if number not in TOOLS_BY_NUMBER:
        raise ValueError(f"Unknown tool number: {number}")
    return TOOLS_BY_NUMBER[number]
