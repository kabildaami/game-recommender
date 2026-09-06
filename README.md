
🎮 GameGem

GameGem is an AI-powered game discovery and recommendation assistant designed for digital gaming platforms.

Modern game stores contain thousands of titles across different genres, moods, platforms, prices, playtimes, and gameplay styles. GameGem helps users navigate that catalog through natural conversation instead of endless scrolling.

Users can ask for recommendations, request detailed information about a specific game, compare options, or simply have a casual gaming conversation with an assistant that understands the catalog.

Thousands of games. One conversation. The right game.
https://github.com/user-attachments/assets/fe4e317d-aaed-4565-97f1-cb6e7ba5d436


✨ Features

🎯 AI Game Recommendations

GameGem recommends games based on natural-language preferences such as:

Genre

Mood / vibe

Platform

Budget

Playtime

Difficulty

Story focus

Co-op / multiplayer preferences

Family-friendly preferences

Similarity to another game

Example queries:

Recommend me a relaxing game for tonight.

I want a co-op PS5 game under $30.

Suggest a story-driven game I can finish in less than 15 hours.

What should I play if I enjoyed Elden Ring?

🔎 Game Details

Users can ask general or highly specific questions about games, including:

Price

Platforms

Genre

Story

Playtime

Difficulty

Multiplayer support

Co-op support

Franchise / series

ESRB rating

Replayability

Language support

Release information

Example:

Tell me about Cyberpunk 2077.

Is Hades available on Nintendo Switch?

How long does Baldur's Gate 3 take to finish?

💬 Multi-Turn Conversation

GameGem maintains conversation state across multiple messages.

Example:

User: Recommend me a cheap RPG on PS5.
Assistant: ...
User: Something shorter.
Assistant: ...
User: Tell me more about the second one.

The assistant keeps track of previous messages and recently retrieved games so follow-up questions remain meaningful.

⚡ Smooth Response Streaming

GameGem streams AI responses in real time.

The backend forwards Groq output immediately while the frontend uses a buffered renderer to display text smoothly, creating a ChatGPT-style typing experience without artificially slowing the model itself.

This provides:

Fast first-token latency

Smooth text appearance

Adaptive rendering speed

Better perceived responsiveness

No unnecessary backend delay

🧠 AI-Based Intent Routing

Each user message is first classified by an AI model into one of three tools:

Tool

Intent

Description

1

Game Recommendation

Uses the RAG pipeline to recommend relevant games

2

General Conversation

Handles greetings and casual conversation

3

Game Details

Retrieves information about a specific game

The classifier returns only 1, 2, or 3 to minimize token usage.

The classifier is model-based rather than keyword-mapped or hardcoded.

🏗️ Architecture

                    ┌─────────────────────────┐
                    │        Frontend         │
                    │   HTML / CSS / JS UI    │
                    └────────────┬────────────┘
                                 │
                                 │ HTTP streaming
                                 ▼
                    ┌─────────────────────────┐
                    │        FastAPI          │
                    │  /api/chat/stream       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      responder.py       │
                    │ Multi-turn conversation │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  intent_classifier.py   │
                    │      AI → 1 / 2 / 3     │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
               ▼                 ▼                 ▼
      ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
      │ Recommendation │ │ General Chat   │ │ Game Details   │
      │     Tool 1     │ │     Tool 2     │ │     Tool 3     │
      └───────┬────────┘ └────────────────┘ └───────┬────────┘
              │                                     │
              └─────────────────┬───────────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │      RAG Retriever      │
                    │       ChromaDB          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Game Knowledge Base    │
                    │    game_database.json   │
                    └─────────────────────────┘

🧩 Project Structure

GameGem/
│
├── frontend/
│   ├── index.html
│   │
│   ├── css/
│   │   └── styles.css
│   │
│   ├── js/
│   │   ├── data.js
│   │   └── app.js
│   │
│   └── assets/
│       └── gamegem-logo.jpg
│
├── fastapi/
│   ├── main.py
│   ├── session_manager.py
│   ├── schemas.py
│   ├── api_settings.py
│   ├── requirements.txt
│   └── .env.example
│
├── rag/
│   ├── __init__.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── saver.py
│   ├── retriever.py
│   ├── pipeline.py
│   ├── game_database.json
│   └── chroma_db/
│
├── config.py
├── register_tools.py
├── intent_classifier.py
├── prompts.py
├── responder.py
├── requirements.txt
├── .env
└── README.md

The fastapi/ directory is intentionally not a Python package. Avoid adding fastapi/__init__.py, because the folder name could otherwise conflict with the installed fastapi library.

🧠 RAG Pipeline

GameGem uses Retrieval-Augmented Generation to ground recommendations and game-detail answers in its local game knowledge base.

RAG Flow

game_database.json
        ↓
   chunker.py
        ↓
   embedder.py
        ↓
    saver.py
        ↓
    ChromaDB
        ↓
  retriever.py
        ↓
  responder.py
        ↓
       Groq

1. chunker.py

The dataset follows a one game = one chunk strategy.

This works well because each game record is already a complete semantic unit containing description, genres, tags, platforms, price, playtime, recommendation features, and a dedicated rag_text field.

Each chunk contains:

chunk_id

text to embed

flattened metadata

Example metadata fields:

title
genres
tags
platforms
price_tier
reference_price_usd
time_commitment
player_modes
franchise
difficulty
co_op
family_friendly

2. embedder.py

Game chunks are converted to vector embeddings using a lightweight SentenceTransformers embedding model.

Default embedding model:

all-MiniLM-L6-v2

This model is fast, CPU-friendly, and suitable for semantic search across a moderate-sized game catalog.

3. saver.py

Embeddings and metadata are stored in ChromaDB for persistent local retrieval.

Default collection:

games

4. retriever.py

The retriever performs semantic similarity search against the ChromaDB game collection.

Recommendation and game-detail queries can use different retrieval depths so recommendations remain diverse while detail queries remain precise.

5. pipeline.py

The RAG build process is orchestrated from one command.

Build or rebuild the vector database with:

python -m rag.pipeline --rebuild

This should be run whenever the game dataset changes significantly.

🎮 Game Dataset

The GameGem dataset is designed specifically for recommendation-oriented RAG.

It can contain fields such as:

{
  "game_id": 1,
  "title": "Cyberpunk 2077",
  "description": "...",
  "primary_category": "Action-Adventure",
  "genres": ["Action RPG", "Open World", "Cyberpunk"],
  "tags": ["story-rich", "open-world", "futuristic"],
  "franchise": "Cyberpunk",
  "platforms": [],
  "player_modes": ["Single-player"],
  "price": {},
  "gameplay_hours": {},
  "language_support": {},
  "recommendation_features": {},
  "rag_text": "..."
}

The enriched dataset supports recommendation queries based on:

Price

Gameplay duration

Franchise

Localization

Platform

Genre

Multiplayer type

Difficulty

Pace

Story focus

Family friendliness

Replayability

🤖 Intent Classification

intent_classifier.py receives:

The current user message

Tool definitions from register_tools.py

Limited conversation context when useful

It sends a minimal classification prompt to Groq and expects only:

1

2

or

3

This keeps the classification stage inexpensive and fast.

Tool Registry

register_tools.py defines the available assistant behaviors.

Conceptually:

1 → Game Recommendation
2 → General Conversation
3 → Game Details

The classifier reads these tool descriptions dynamically instead of duplicating routing logic.

💬 Responder

responder.py is the main conversational intelligence layer.

It handles:

Intent classification

Routing

RAG retrieval

Groq generation

Conversation history

Recently retrieved game context

Token statistics

Streaming responses

Multi-Turn Memory

Groq API requests are stateless, so GameGem manages conversation history itself.

Conversation messages are stored as:

[
    {"role": "user", "content": "Recommend me an RPG"},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "Something cheaper"}
]

Recent conversation turns are sent back to the model on each request.

The maximum amount of API history can be configured to control token usage.

Retrieval-Aware Follow-Ups

GameGem also remembers recently retrieved game titles.

This improves requests such as:

What about the second one?

or:

Is that one available on Switch?

⚡ Streaming Architecture

GameGem uses streaming from Groq all the way to the browser.

Groq stream
    ↓
responder.py
    ↓
FastAPI StreamingResponse
    ↓
Fetch ReadableStream
    ↓
Frontend display buffer
    ↓
Smooth rendered response

The backend does not intentionally sleep between chunks.

Instead, the browser controls visual pacing using an adaptive text buffer.

This allows the backend to remain fast while the UI remains smooth.

🌐 FastAPI Backend

The FastAPI layer connects the browser interface to GameGem's conversational engine.

Primary endpoints include:

GET     /
GET     /api/health
POST    /api/chat
POST    /api/chat/stream
GET     /api/sessions/{session_id}/history
GET     /api/sessions/{session_id}/stats
DELETE  /api/sessions/{session_id}

Streaming Endpoint

The frontend primarily uses:

POST /api/chat/stream

Request example:

{
  "message": "Recommend me a cheap co-op game on PS5",
  "session_id": "optional-existing-session-id"
}

The server returns streamed text.

The session ID is returned through a response header and reused by the frontend.

🧠 Session Management

Each browser session receives its own GameChatResponder instance.

Browser A
   ↓
Session A
   ↓
Responder A
   ↓
Conversation A

Browser B
   ↓
Session B
   ↓
Responder B
   ↓
Conversation B

During local development, sessions are stored in application memory.

For a production deployment with multiple workers, a shared session store such as Redis should be used instead.

🎨 Frontend

The GameGem interface is built with:

HTML

CSS

Vanilla JavaScript

The design uses a premium dark gaming aesthetic with:

GameGem branding

Cinematic featured-game carousel

Auto-rotating hero games

Keyboard navigation

Mouse/touch swipe support

Hover-revealed navigation controls

Interactive game cards

Search and filter chips

Game detail modal

Floating AI assistant

Responsive design

Smooth streamed AI responses

AI Assistant UX

The GameGem AI window supports:

Enter       → Send message
Shift+Enter → New line

The assistant launcher toggles the chat window open and closed.

The streaming display includes:

Typing indicator before first token

Smooth adaptive text rendering

Streaming cursor

Auto-growing message field

Disabled duplicate submissions during generation

🛠️ Technology Stack

AI / LLM

Groq API

ALLaM / configurable lightweight classifier model

Qwen / configurable response model

RAG

SentenceTransformers

ChromaDB

all-MiniLM-L6-v2

Backend

FastAPI

Uvicorn

Pydantic

Python

Frontend

HTML5

CSS3

Vanilla JavaScript

Fetch API / ReadableStream

🚀 Installation

1. Clone the project

git clone <your-repository-url>
cd GameGem

2. Create a virtual environment

Windows

python -m venv .venv
.venv\Scripts\activate

macOS / Linux

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

If you maintain FastAPI dependencies separately:

pip install -r fastapi/requirements.txt

🔐 Environment Variables

Create a .env file in the project root.

Example:

GROQ_API_KEY=your_groq_api_key_here

Depending on your configuration, you may also expose model settings such as:

INTENT_MODEL=allam-2-7b
GENERAL_MODEL=allam-2-7b
RAG_MODEL=qwen/qwen3.8-27b
DETAIL_MODEL=qwen/qwen3.8-27b
MAX_HISTORY_TURNS=8

Use the exact model IDs currently available in your Groq account.

🗃️ Add the Game Database

Place the complete GameGem dataset at:

rag/game_database.json

🧱 Build the Vector Database

Run:

python -m rag.pipeline --rebuild

This creates / updates the persistent ChromaDB collection.

You normally only need to rebuild after changing the dataset or embedding configuration.

▶️ Run GameGem

From the project root:

uvicorn --app-dir fastapi main:app --reload --host 127.0.0.1 --port 8000

Then open:

http://127.0.0.1:8000

Do not open frontend/index.html directly using file:// when testing the full application because the frontend needs access to the FastAPI API routes.

🧪 Health Check

Open:

http://127.0.0.1:8000/api/health

or:

curl http://127.0.0.1:8000/api/health

💻 CLI Chat

The responder can also be tested without the browser.

python responder.py

Typical commands:

/clear
/history
/stats
/quit

🧪 Example Test Queries

Recommendation

Recommend me a difficult RPG on PC.

I want a relaxing Nintendo Switch game under $25.

Find me a co-op game for two players.

Game Details

Tell me everything important about Cyberpunk 2077.

How long is Hades?

Is The Witcher 3 available on Switch?

General Conversation

Hey GameGem, how are you?

📊 Recommended Evaluation Metrics

To evaluate GameGem beyond manual testing, consider building a benchmark set and measuring:

Intent Classification

Accuracy
Confusion matrix
Latency
Tokens per classification

Retrieval

Hit@K
Recall@K
MRR
Constraint satisfaction

Generation

Groundedness
Recommendation relevance
Hallucination rate
Response latency
Tokens per response

UX

Time to first token
Streaming smoothness
Total response time
Session retention
User recommendation acceptance

🔮 Future Improvements

Potential next steps include:

Hybrid semantic + metadata-filtered retrieval

Query constraint extraction

Reranking

Redis session storage

Authentication

User preference profiles

Recommendation history

Wishlist integration

Live storefront pricing APIs

Steam / Epic / PlayStation / Xbox store integrations

User ratings and feedback loops

Recommendation explanations

Collaborative filtering

Personalized embeddings

Voice interaction

Mobile application

📈 Production Considerations

The current architecture is excellent for development, demos, portfolio use, and small deployments.

For larger production deployment, consider:

Redis for sessions

Multiple Uvicorn/Gunicorn workers

Reverse proxy such as Nginx

HTTPS

Rate limiting

API authentication

Request logging

Error monitoring

Persistent user accounts

Analytics

Automated RAG evaluation

Vector DB backup strategy

For streaming behind a reverse proxy, ensure proxy buffering is disabled.

🎯 Vision

Game distribution platforms increasingly compete on catalog size, but larger catalogs also increase choice overload.

GameGem explores a different interaction model:

Instead of making users navigate thousands of games manually, give every player an intelligent assistant that understands the catalog and helps them find the right experience through conversation.

GameGem can act as:

A recommendation engine

A game knowledge assistant

A catalog navigation layer

A comparison assistant

A gaming companion

The long-term vision is for AI assistants like GameGem to become a natural interface between players and large digital game libraries.


💎 GameGem

Discover. Play. Belong.
