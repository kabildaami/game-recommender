"""Load the game JSON database and create one retrieval chunk per game."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config import DATABASE_PATH


@dataclass
class GameChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def _join(values: Iterable[Any]) -> str:
    return ", ".join(str(v) for v in values if v is not None and str(v).strip())


class GameChunker:
    """Create one semantically rich chunk per game.

    The supplied dataset already has one logical entity per game, so splitting a
    game into arbitrary token windows would weaken recommendation retrieval.
    """

    def __init__(self, data_path: Path | str = DATABASE_PATH) -> None:
        self.data_path = Path(data_path)
        self.games: List[Dict[str, Any]] = []

    def load_games(self) -> List[Dict[str, Any]]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Game database not found: {self.data_path}")

        with self.data_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if isinstance(data, dict) and isinstance(data.get("games"), list):
            self.games = data["games"]
        elif isinstance(data, list):
            self.games = data
        else:
            raise ValueError(
                "game_database.json must be either a JSON list or an object with a 'games' list."
            )
        return self.games

    @staticmethod
    def _build_fallback_text(game: Dict[str, Any]) -> str:
        fields: List[str] = []
        title = game.get("title")
        if title:
            fields.append(str(title))
        if game.get("description"):
            fields.append(str(game["description"]))
        if game.get("genres"):
            fields.append(f"Genres: {_join(game['genres'])}.")
        if game.get("tags"):
            fields.append(f"Tags: {_join(game['tags'][:12])}.")

        platforms = game.get("platforms") or []
        names = [p.get("name") for p in platforms if isinstance(p, dict)]
        if names:
            fields.append(f"Platforms: {_join(names)}.")

        price = game.get("price") or {}
        if price:
            if price.get("reference_price_usd") is not None:
                fields.append(f"Reference price USD: {price['reference_price_usd']}.")
            if price.get("price_tier"):
                fields.append(f"Price tier: {price['price_tier']}.")

        gameplay = game.get("gameplay_hours") or {}
        if gameplay.get("time_commitment"):
            fields.append(f"Time commitment: {gameplay['time_commitment']}.")

        if game.get("franchise"):
            fields.append(f"Franchise: {game['franchise']}.")
        return " ".join(fields).strip()

    @staticmethod
    def flatten_metadata(game: Dict[str, Any]) -> Dict[str, Any]:
        """Keep compact scalar metadata that Chroma can safely store."""
        meta: Dict[str, Any] = {}

        scalar_fields = (
            "game_id",
            "title",
            "description",
            "primary_category",
            "esrb_rating",
            "user_rating_5",
            "metacritic_score",
            "developer",
            "publisher",
            "franchise",
        )
        for field in scalar_fields:
            value = game.get(field)
            if value is not None and isinstance(value, (str, int, float, bool)):
                # Description is kept short in metadata because the full text is a document.
                if field == "description":
                    value = str(value)[:600]
                meta[field] = value

        for field in ("genres", "tags", "player_modes"):
            values = game.get(field)
            if isinstance(values, list) and values:
                meta[field] = _join(values[:15])

        platforms = game.get("platforms") or []
        if isinstance(platforms, list):
            platform_names = [
                p.get("name") for p in platforms if isinstance(p, dict) and p.get("name")
            ]
            if platform_names:
                meta["platforms"] = _join(platform_names)

        release = game.get("release") or {}
        if release.get("first_release_year") is not None:
            meta["release_year"] = release["first_release_year"]
        if release.get("first_release_date"):
            meta["release_date"] = release["first_release_date"]

        price = game.get("price") or {}
        for source, target in (
            ("pricing_model", "pricing_model"),
            ("reference_price_usd", "reference_price_usd"),
            ("price_tier", "price_tier"),
        ):
            value = price.get(source)
            if value is not None:
                meta[target] = value

        gameplay = game.get("gameplay_hours") or {}
        for key in ("time_commitment", "replayability"):
            if gameplay.get(key) is not None:
                meta[key] = gameplay[key]
        main_story = gameplay.get("main_story_hours") or {}
        completionist = gameplay.get("completionist_hours") or {}
        if main_story.get("min") is not None:
            meta["main_story_min_hours"] = main_story["min"]
        if main_story.get("max") is not None:
            meta["main_story_max_hours"] = main_story["max"]
        if completionist.get("min") is not None:
            meta["completionist_min_hours"] = completionist["min"]
        if completionist.get("max") is not None:
            meta["completionist_max_hours"] = completionist["max"]

        features = game.get("recommendation_features") or {}
        for key in (
            "difficulty",
            "pace",
            "story_focus",
            "co_op",
            "competitive_multiplayer",
            "family_friendly",
            "online_required",
        ):
            value = features.get(key)
            if value is not None and isinstance(value, (str, int, float, bool)):
                meta[key] = value

        language = game.get("language_support") or {}
        interface = language.get("interface_and_subtitle_languages") or []
        audio = language.get("full_audio_languages") or []
        if interface:
            meta["interface_languages"] = _join(interface)
        if audio:
            meta["audio_languages"] = _join(audio)

        return meta

    def create_chunks(self) -> List[GameChunk]:
        if not self.games:
            self.load_games()

        chunks: List[GameChunk] = []
        for index, game in enumerate(self.games, start=1):
            text = str(game.get("rag_text") or "").strip()
            if not text:
                text = self._build_fallback_text(game)
            if not text:
                continue

            game_id = game.get("game_id", index)
            chunk_id = f"game_{game_id}"
            metadata = self.flatten_metadata(game)
            metadata["chunk_id"] = chunk_id
            chunks.append(GameChunk(chunk_id=chunk_id, text=text, metadata=metadata))

        return chunks
