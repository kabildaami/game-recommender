"""Central configuration for the game recommendation chatbot.

All runtime settings can be overridden with environment variables.
Paths are resolved from the project directory, so the app works regardless
of the shell's current working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

RAG_DIR = PROJECT_ROOT / "rag"
DATABASE_PATH = Path(os.getenv("GAME_DATABASE_PATH", RAG_DIR / "game_database.json"))
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", RAG_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "games")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

# Small/fast model for a single-token routing decision.
INTENT_MODEL = os.getenv("GROQ_INTENT_MODEL", "allam-2-7b")

# Short small-talk does not need the larger RAG answer model.
GENERAL_MODEL = os.getenv("GROQ_GENERAL_MODEL", "allam-2-7b")

# Qwen is used in non-reasoning/instruct mode for grounded answers.
RAG_MODEL = os.getenv("GROQ_RAG_MODEL", "qwen/qwen3.8-27b")
DETAIL_MODEL = os.getenv("GROQ_DETAIL_MODEL", RAG_MODEL)

INTENT_MAX_TOKENS = int(os.getenv("INTENT_MAX_TOKENS", "2"))
GENERAL_MAX_TOKENS = int(os.getenv("GENERAL_MAX_TOKENS", "140"))
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "420"))
DETAIL_MAX_TOKENS = int(os.getenv("DETAIL_MAX_TOKENS", "360"))

RECOMMENDATION_TOP_K = int(os.getenv("RECOMMENDATION_TOP_K", "6"))
DETAIL_TOP_K = int(os.getenv("DETAIL_TOP_K", "3"))

# Conversation memory: all turns are retained in self.messages, while only the
# newest N turns are resent to Groq to avoid unbounded prompt growth.
# Set to 0 to resend the entire session history on every turn.
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "8"))
CLASSIFIER_HISTORY_MESSAGES = int(os.getenv("CLASSIFIER_HISTORY_MESSAGES", "2"))
CLASSIFIER_CONTEXT_CHARS = int(os.getenv("CLASSIFIER_CONTEXT_CHARS", "220"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
