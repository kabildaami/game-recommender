"""Runtime semantic retriever for recommendation and game-detail queries."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import chromadb

from config import CHROMA_PATH, COLLECTION_NAME, DETAIL_TOP_K, RECOMMENDATION_TOP_K
from rag.embedder import GameEmbedder


@dataclass
class RetrievedGame:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    distance: float | None

    @property
    def similarity(self) -> float | None:
        if self.distance is None:
            return None
        # Collection uses cosine distance: smaller is better.
        return 1.0 - self.distance


class GameRetriever:
    def __init__(
        self,
        persist_dir: Path | str = CHROMA_PATH,
        collection_name: str = COLLECTION_NAME,
        embedder: GameEmbedder | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedder = embedder or GameEmbedder()
        self._client = None
        self._collection = None

    def _ensure_collection(self) -> None:
        if self._collection is not None:
            return
        if not self.persist_dir.exists():
            raise FileNotFoundError(
                f"Vector database not found at {self.persist_dir}. "
                "Run: python -m rag.pipeline --rebuild"
            )
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        try:
            self._collection = self._client.get_collection(self.collection_name)
        except Exception as exc:
            raise RuntimeError(
                f"Chroma collection '{self.collection_name}' is missing. "
                "Run: python -m rag.pipeline --rebuild"
            ) from exc

    def retrieve(self, query: str, k: int = RECOMMENDATION_TOP_K) -> List[RetrievedGame]:
        self._ensure_collection()
        if not query.strip():
            return []

        query_vector = self.embedder.embed_query(query)
        count = self._collection.count()
        n_results = min(max(1, k), count) if count else 1
        result = self._collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        output: List[RetrievedGame] = []
        for i, chunk_id in enumerate(ids):
            output.append(
                RetrievedGame(
                    chunk_id=chunk_id,
                    text=docs[i] if i < len(docs) else "",
                    metadata=metas[i] if i < len(metas) and metas[i] else {},
                    distance=distances[i] if i < len(distances) else None,
                )
            )
        return output

    def recommend(self, query: str) -> List[RetrievedGame]:
        return self.retrieve(query, k=RECOMMENDATION_TOP_K)

    def details(self, query: str) -> List[RetrievedGame]:
        return self.retrieve(query, k=DETAIL_TOP_K)

    @staticmethod
    def _value(meta: Dict[str, Any], key: str, fallback: str = "unknown") -> str:
        value = meta.get(key)
        return str(value) if value not in (None, "") else fallback

    def format_for_prompt(self, games: List[RetrievedGame], mode: str) -> str:
        if not games:
            return "NO_MATCHES"

        blocks: List[str] = []
        for rank, item in enumerate(games, start=1):
            m = item.metadata
            title = self._value(m, "title", "Unknown title")

            if mode == "recommendation":
                snippet = item.text[:260].replace("\n", " ")
                block = (
                    f"[{rank}] {title}\n"
                    f"genres={self._value(m, 'genres')} | platforms={self._value(m, 'platforms')} | "
                    f"price=${self._value(m, 'reference_price_usd')} ({self._value(m, 'price_tier')}) | "
                    f"time={self._value(m, 'time_commitment')} | difficulty={self._value(m, 'difficulty')} | "
                    f"modes={self._value(m, 'player_modes')} | coop={self._value(m, 'co_op')}\n"
                    f"summary={snippet}"
                )
            else:
                snippet = item.text[:520].replace("\n", " ")
                block = (
                    f"[{rank}] {title}\n"
                    f"description={self._value(m, 'description', snippet)}\n"
                    f"genres={self._value(m, 'genres')}\n"
                    f"platforms={self._value(m, 'platforms')}\n"
                    f"release={self._value(m, 'release_date')} / {self._value(m, 'release_year')}\n"
                    f"price_usd={self._value(m, 'reference_price_usd')} | price_tier={self._value(m, 'price_tier')}\n"
                    f"main_story_hours={self._value(m, 'main_story_min_hours')}-{self._value(m, 'main_story_max_hours')} | "
                    f"completionist_hours={self._value(m, 'completionist_min_hours')}-{self._value(m, 'completionist_max_hours')}\n"
                    f"modes={self._value(m, 'player_modes')} | difficulty={self._value(m, 'difficulty')} | "
                    f"pace={self._value(m, 'pace')} | story_focus={self._value(m, 'story_focus')}\n"
                    f"coop={self._value(m, 'co_op')} | competitive={self._value(m, 'competitive_multiplayer')} | "
                    f"family_friendly={self._value(m, 'family_friendly')} | online_required={self._value(m, 'online_required')}\n"
                    f"franchise={self._value(m, 'franchise')} | ESRB={self._value(m, 'esrb_rating')} | "
                    f"user_rating_5={self._value(m, 'user_rating_5')} | metacritic={self._value(m, 'metacritic_score')}\n"
                    f"interface_languages={self._value(m, 'interface_languages')}\n"
                    f"audio_languages={self._value(m, 'audio_languages')}\n"
                    f"rag_summary={snippet}"
                )
            blocks.append(block)

        return "\n\n".join(blocks)
