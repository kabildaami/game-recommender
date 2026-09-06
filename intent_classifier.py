"""AI-only intent classifier.

Contract:
    classify(...) -> 1, 2, or 3

No keyword matching, regular-expression routing, title list, or sentence-to-intent
mapping is used. A Groq-hosted language model makes the routing decision from the
registered tool briefings.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from groq import Groq

from config import (
    CLASSIFIER_CONTEXT_CHARS,
    CLASSIFIER_HISTORY_MESSAGES,
    GROQ_API_KEY,
    INTENT_MAX_TOKENS,
    INTENT_MODEL,
)
from prompts import INTENT_SYSTEM_PROMPT
from register_tools import get_classifier_briefing


class IntentClassifier:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = INTENT_MODEL,
    ) -> None:
        key = api_key or GROQ_API_KEY
        if not key:
            raise ValueError("GROQ_API_KEY is missing. Add it to .env.")
        self.client = Groq(api_key=key)
        self.model = model
        self.tools_brief = get_classifier_briefing()

    @staticmethod
    def _compact_history(history: Optional[List[Dict[str, str]]]) -> str:
        if not history:
            return ""
        selected = history[-CLASSIFIER_HISTORY_MESSAGES:]
        parts = []
        for item in selected:
            role = item.get("role", "")
            content = str(item.get("content", ""))[:CLASSIFIER_CONTEXT_CHARS]
            if role in {"user", "assistant"} and content:
                parts.append(f"{role[0].upper()}:{content}")
        return " | ".join(parts)

    def _request_route(self, user_text: str, history_text: str = "") -> str:
        # Tool definitions come from register_tools.py, not from routing code.
        prompt = f"TOOLS\n{self.tools_brief}\n"
        if history_text:
            prompt += f"RECENT\n{history_text}\n"
        prompt += f"MESSAGE\n{user_text.strip()}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=INTENT_MAX_TOKENS,
            stop=["\n"],
        )
        return (response.choices[0].message.content or "").strip()

    def classify(
        self,
        user_text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> int:
        if not user_text or not user_text.strip():
            return 2

        history_text = self._compact_history(conversation_history)
        raw = self._request_route(user_text, history_text)

        # Parsing is strict, but the decision itself is always model-based.
        if raw in {"1", "2", "3"}:
            return int(raw)

        # One tiny model retry instead of falling back to keyword rules.
        retry = self._request_route(
            f"Choose one number only for this message: {user_text}",
            history_text,
        )
        for char in retry:
            if char in "123":
                return int(char)

        # Safe operational fallback on malformed/API-compatible output only.
        # It is not a sentence/keyword routing rule.
        return 2


if __name__ == "__main__":
    classifier = IntentClassifier()
    text = input("Message: ")
    print(classifier.classify(text))
