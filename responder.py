"""Multi-turn GameGem responder using Groq + local RAG.

Flow per turn:
    user text
      -> IntentClassifier (AI model returns 1/2/3)
      -> local route
      -> optional RAG retrieval
      -> Groq response generation with prior conversation messages
      -> append clean user/assistant turns to local conversation history

The Groq API is stateless. This class owns conversation state explicitly.

Two public response modes are provided:
    respond(text)      -> complete response (useful for CLI/tests)
    stream_chat(text)  -> iterator of text chunks (useful for FastAPI/UI)
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from config import (
    DETAIL_MAX_TOKENS,
    DETAIL_MODEL,
    GENERAL_MAX_TOKENS,
    GENERAL_MODEL,
    GROQ_API_KEY,
    MAX_HISTORY_TURNS,
    RAG_MAX_TOKENS,
    RAG_MODEL,
)
from intent_classifier import IntentClassifier
from prompts import DETAIL_SYSTEM_PROMPT, GENERAL_SYSTEM_PROMPT, RECOMMENDATION_SYSTEM_PROMPT
from rag.retriever import GameRetriever
from register_tools import get_tool


def add_user_message(messages: List[Dict[str, str]], text: str) -> None:
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages: List[Dict[str, str]], text: str) -> None:
    messages.append({"role": "assistant", "content": text})


class GameChatResponder:
    """Stateful GameGem conversation responder.

    Create one instance per browser/session. The FastAPI session manager included
    with this project does exactly that.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_history_turns: int = MAX_HISTORY_TURNS,
    ) -> None:
        key = api_key or GROQ_API_KEY
        if not key:
            raise ValueError("GROQ_API_KEY is missing. Add it to .env.")

        self.client = Groq(api_key=key)
        self.intent_classifier = IntentClassifier(api_key=key)
        self._retriever: GameRetriever | None = None

        # Full local session history. Only clean user/assistant turns are stored.
        self.messages: List[Dict[str, str]] = []
        self.max_history_turns = max_history_turns

        self.total_turns = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.route_counts = {1: 0, 2: 0, 3: 0}
        self.last_route: int | None = None
        self.last_retrieved_titles: List[str] = []

    @property
    def retriever(self) -> GameRetriever:
        # A greeting should not load the sentence-transformer model.
        if self._retriever is None:
            self._retriever = GameRetriever()
        return self._retriever

    def _history_for_api(self) -> List[Dict[str, str]]:
        if self.max_history_turns <= 0:
            return list(self.messages)
        max_messages = self.max_history_turns * 2
        return list(self.messages[-max_messages:])

    def _retrieval_query(self, user_text: str) -> str:
        """Add compact conversational context to semantic retrieval."""
        previous_user = ""
        for message in reversed(self.messages):
            if message.get("role") == "user":
                previous_user = message.get("content", "")[:280]
                break

        titles = ", ".join(self.last_retrieved_titles[:4])
        pieces = [f"Current request: {user_text.strip()}"]
        if previous_user:
            pieces.append(f"Previous user request: {previous_user}")
        if titles:
            pieces.append(f"Recently retrieved games: {titles}")
        return "\n".join(pieces)

    def _completion_kwargs(
        self,
        *,
        system_prompt: str,
        current_user_content: str,
        model: str,
        max_tokens: int,
        use_non_reasoning_mode: bool,
    ) -> Dict[str, Any]:
        api_messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            *self._history_for_api(),
            {"role": "user", "content": current_user_content},
        ]

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "temperature": 0.55,
            "max_tokens": max_tokens,
        }
        if use_non_reasoning_mode and model.startswith("qwen/"):
            kwargs["reasoning_effort"] = "none"
        return kwargs

    def _completion(
        self,
        *,
        system_prompt: str,
        current_user_content: str,
        model: str,
        max_tokens: int,
        use_non_reasoning_mode: bool,
    ) -> str:
        kwargs = self._completion_kwargs(
            system_prompt=system_prompt,
            current_user_content=current_user_content,
            model=model,
            max_tokens=max_tokens,
            use_non_reasoning_mode=use_non_reasoning_mode,
        )
        result = self.client.chat.completions.create(**kwargs)
        text = (result.choices[0].message.content or "").strip()

        usage = getattr(result, "usage", None)
        if usage is not None:
            self.total_prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            self.total_completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        return text

    def _completion_stream(
        self,
        *,
        system_prompt: str,
        current_user_content: str,
        model: str,
        max_tokens: int,
        use_non_reasoning_mode: bool,
    ) -> Iterator[str]:
        """Yield Groq completion text as it arrives.

        Groq's Chat Completions streaming API emits chunks whose text is in
        chunk.choices[0].delta.content. We forward only non-empty text deltas.
        """
        kwargs = self._completion_kwargs(
            system_prompt=system_prompt,
            current_user_content=current_user_content,
            model=model,
            max_tokens=max_tokens,
            use_non_reasoning_mode=use_non_reasoning_mode,
        )
        kwargs["stream"] = True

        stream = self.client.chat.completions.create(**kwargs)
        final_usage = None

        for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                final_usage = usage

            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            piece = getattr(delta, "content", None) if delta is not None else None
            if piece:
                yield piece

        # Some Groq SDK/API versions expose usage on the final stream chunk.
        # If it is present we keep the same counters as the non-streaming path.
        if final_usage is not None:
            self.total_prompt_tokens += int(getattr(final_usage, "prompt_tokens", 0) or 0)
            self.total_completion_tokens += int(getattr(final_usage, "completion_tokens", 0) or 0)

    def _prepare_recommendation(self, user_text: str) -> str:
        query = self._retrieval_query(user_text)
        games = self.retriever.recommend(query)
        self.last_retrieved_titles = [
            str(item.metadata.get("title", "")) for item in games if item.metadata.get("title")
        ]
        context = self.retriever.format_for_prompt(games, mode="recommendation")
        return f"USER REQUEST\n{user_text}\n\nRETRIEVED GAMES\n{context}"

    def _prepare_details(self, user_text: str) -> str:
        query = self._retrieval_query(user_text)
        games = self.retriever.details(query)
        self.last_retrieved_titles = [
            str(item.metadata.get("title", "")) for item in games if item.metadata.get("title")
        ]
        context = self.retriever.format_for_prompt(games, mode="details")
        return f"USER QUESTION\n{user_text}\n\nRETRIEVED GAME DATA\n{context}"

    def _route_recommendation(self, user_text: str) -> str:
        content = self._prepare_recommendation(user_text)
        return self._completion(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            current_user_content=content,
            model=RAG_MODEL,
            max_tokens=RAG_MAX_TOKENS,
            use_non_reasoning_mode=True,
        )

    def _route_recommendation_stream(self, user_text: str) -> Iterator[str]:
        content = self._prepare_recommendation(user_text)
        yield from self._completion_stream(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            current_user_content=content,
            model=RAG_MODEL,
            max_tokens=RAG_MAX_TOKENS,
            use_non_reasoning_mode=True,
        )

    def _route_general(self, user_text: str) -> str:
        return self._completion(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            current_user_content=user_text,
            model=GENERAL_MODEL,
            max_tokens=GENERAL_MAX_TOKENS,
            use_non_reasoning_mode=False,
        )

    def _route_general_stream(self, user_text: str) -> Iterator[str]:
        yield from self._completion_stream(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            current_user_content=user_text,
            model=GENERAL_MODEL,
            max_tokens=GENERAL_MAX_TOKENS,
            use_non_reasoning_mode=False,
        )

    def _route_details(self, user_text: str) -> str:
        content = self._prepare_details(user_text)
        return self._completion(
            system_prompt=DETAIL_SYSTEM_PROMPT,
            current_user_content=content,
            model=DETAIL_MODEL,
            max_tokens=DETAIL_MAX_TOKENS,
            use_non_reasoning_mode=True,
        )

    def _route_details_stream(self, user_text: str) -> Iterator[str]:
        content = self._prepare_details(user_text)
        yield from self._completion_stream(
            system_prompt=DETAIL_SYSTEM_PROMPT,
            current_user_content=content,
            model=DETAIL_MODEL,
            max_tokens=DETAIL_MAX_TOKENS,
            use_non_reasoning_mode=True,
        )

    def _classify_route(self, text: str) -> int:
        route = self.intent_classifier.classify(text, self.messages)
        if route not in (1, 2, 3):
            route = 2

        self.last_route = route
        self.route_counts[route] = self.route_counts.get(route, 0) + 1
        self.total_turns += 1
        return route

    def respond(self, user_text: str) -> Tuple[str, int]:
        """Generate a complete, non-streaming answer."""
        text = user_text.strip()
        if not text:
            return "Please type a message.", 2

        route = self._classify_route(text)

        # Current text is appended AFTER generation so it is not duplicated in
        # the API history; generation gets the current turn exactly once.
        if route == 1:
            answer = self._route_recommendation(text)
        elif route == 3:
            answer = self._route_details(text)
        else:
            answer = self._route_general(text)

        add_user_message(self.messages, text)
        add_assistant_message(self.messages, answer)
        return answer, route

    def stream_respond(self, user_text: str) -> Iterator[str]:
        """Yield a response chunk-by-chunk and store the final assembled turn.

        Conversation history is updated only after the stream completes
        successfully. If a browser disconnects/cancels midway, a partial answer
        is not inserted into future model context.
        """
        text = user_text.strip()
        if not text:
            yield "Please type a message."
            return

        route = self._classify_route(text)
        if route == 1:
            source = self._route_recommendation_stream(text)
        elif route == 3:
            source = self._route_details_stream(text)
        else:
            source = self._route_general_stream(text)

        pieces: List[str] = []
        completed = False
        try:
            for piece in source:
                pieces.append(piece)
                yield piece
            completed = True
        finally:
            if completed:
                answer = "".join(pieces).strip()
                if answer:
                    add_user_message(self.messages, text)
                    add_assistant_message(self.messages, answer)

    def chat(self, user_text: str) -> str:
        answer, _ = self.respond(user_text)
        return answer

    def stream_chat(self, user_text: str) -> Iterator[str]:
        """Convenience alias used by the FastAPI streaming endpoint."""
        yield from self.stream_respond(user_text)

    def clear_history(self) -> None:
        self.messages.clear()
        self.last_retrieved_titles.clear()
        self.last_route = None

    def get_history(self) -> List[Dict[str, str]]:
        return list(self.messages)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "turns": self.total_turns,
            "route_counts": dict(self.route_counts),
            "last_route": self.last_route,
            "last_route_name": get_tool(self.last_route).name if self.last_route else None,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "tracked_messages": len(self.messages),
            "api_history_turn_limit": self.max_history_turns,
        }


def interactive_chat() -> None:
    bot = GameChatResponder()
    print("Game chatbot ready. Commands: /clear, /history, /stats, /quit")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not text:
            continue
        if text.lower() in {"/quit", "/exit"}:
            print("Bye!")
            break
        if text.lower() == "/clear":
            bot.clear_history()
            print("Conversation cleared.")
            continue
        if text.lower() == "/history":
            for item in bot.get_history():
                print(f"{item['role']}: {item['content']}")
            continue
        if text.lower() == "/stats":
            print(bot.get_stats())
            continue

        try:
            print("Bot: ", end="", flush=True)
            for chunk in bot.stream_chat(text):
                print(chunk, end="", flush=True)
            print()
        except Exception as exc:
            print(f"\nError: {exc}")


if __name__ == "__main__":
    interactive_chat()
