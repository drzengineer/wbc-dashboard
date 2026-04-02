# WBC Dashboard

Full-stack data engineering + AI application — MLB Stats API → PostgreSQL → dbt → Dagster → pgvector RAG → SvelteKit

**Built in 14 days · March 2026 · Live at [wbc.davidr.io](https://wbc.davidr.io)**

---

## What it does

A production-deployed analytics dashboard for every World Baseball Classic season (2006–2026), with an AI chat interface powered by a custom RAG pipeline. Users can browse standings, game results, and player stats across all WBC tournaments — and ask natural-language questions answered by an LLM grounded in the actual tournament data.

| Route | What's there |
|---|---|
| `/` | Tournament standings, bracket (Championship → SF → QF), recent results |
| `/games` | Full game browser — season tabs, round filters, score cards |
| `/players` | Batting/pitching leaderboards with stat filters (AVG / HR / RBI / OPS / ERA / K / IP) |
| `/players/[id]` | Individual player profile — career totals, season splits, game-by-game log |
| `/chat` | AI chat — streaming responses grounded in 16K+ embedded sentences |

---

## Architecture

![Architecture diagram](assets/architecture.svg)

The pipeline follows an ELT pattern: raw JSON from the MLB Stats API lands directly in Supabase as JSONB, then dbt handles all transforms inside the database. Embeddings are generated locally and stored in a pgvector table alongside the analytics data — no separate vector DB needed at this scale (~50K rows).

---

## Stack

| Layer | Technology | Decision |
|---|---|---|
| Ingestion | Python | ELT pattern — raw load first, transform in DB |
| Database | PostgreSQL via Supabase | Managed Postgres, pgvector built in, three-schema design |
| Transforms | dbt | SQL models with automated testing, lineage, documentation |
| Orchestration | Dagster | Software-defined assets, native dbt integration; chosen over Airflow (EOL 2026) |
| Vector storage | pgvector (HNSW) | Consolidated inside existing Postgres — no separate vector DB at this scale |
| Embeddings | all-MiniLM-L6-v2 (local) | Free, no rate limits, 384 dims, embeds 16K+ rows in ~1 min on CPU |
| LLM | Groq llama-3.3-70b-versatile | Free tier, streaming, no LangChain abstraction layer |
| Frontend + API | SvelteKit + TypeScript | Full-stack in one deployment, Svelte 5 runes throughout |
| Containerization | Docker | Pipeline runs as one image; credentials injected at runtime via `entrypoint.sh` |
| Frontend deploy | Vercel | Native SvelteKit adapter, zero config |
| Pipeline deploy | AWS EC2 (m7i-flex.large) | Fixed CPU baseline — eliminates burst credit risk that froze a t2.small during embedding |
| CI/CD | GitHub Actions | dbt tests on every push; auto-deploy to EC2 on `pipeline/**` changes |

---

## Key engineering decisions

**ELT over ETL.** Raw API data lands in PostgreSQL as JSONB without transformation. dbt handles all transforms inside the database — clean separation of ingestion and modeling concerns.

**PostgreSQL over Snowflake.** Dataset is ~50K rows. Snowflake is built for hundreds of millions. Right tool for the data volume; demonstrates understanding of OLTP vs OLAP tradeoffs.

**pgvector (HNSW) over Pinecone.** Vector storage consolidated inside existing PostgreSQL. No performance justification for a separate vector DB at this scale. Switching the index from ivfflat to HNSW improved similarity scores from ~0.39 to ~0.66, with better recall and no training-data requirement.

**Dagster over Airflow.** Airflow 2 is approaching end of life in 2026. Dagster models pipelines as software-defined assets — each dbt model surfaces individually in the UI with first-class lineage.

**Local embeddings over VoyageAI.** Switched from VoyageAI voyage-4-lite (1024 dims, rate-limited, requires an API key) to all-MiniLM-L6-v2. Embeds 16K+ sentences per run with zero API cost or rate limits.

**No LangChain.** The RAG pipeline uses direct fetch to the local SentenceTransformer, a Supabase RPC, and the Groq SDK. Eliminates the abstraction layer — full mechanical understanding of every step.

**Pre-embedding question rewriting.** Before vector search, a lightweight Groq call (`temperature=0`, `max_tokens=128`) rewrites the user's question into a standalone query by resolving pronouns and adding conversation context — "He" → "Shohei Ohtani", "What about 2023?" → the full question. This substantially improves embedding similarity scores for follow-up questions. The final answer generation receives only the rewritten question and retrieved context, not the chat history, so the LLM stays grounded in retrieved data rather than prior answers.

**Sentence engineering over raw prose.** Structured analytics data was converted into natural-language sentences before embedding, including explicit Q&A pairs for knockout round games. This yields similarity scores of 0.7+ vs ~0.4 for raw data, because the quality of text representation directly determines retrieval quality.

---

## RAG pipeline

```
User message + conversation history
        ↓
rewriteQuestion() — Groq (temp=0, max_tokens=128)
  Resolves pronouns, adds year/team context from history
  Strictly rewrites — never answers
        ↓
embedQuestion() — local all-MiniLM-L6-v2 via @xenova/transformers
  384-dim vector
        ↓
retrieveContext() — vectors.match_embeddings RPC (Supabase)
  HNSW cosine similarity, match_count=40, threshold=0.4
        ↓
queryRagStream() — Groq SDK (llama-3.3-70b-versatile)
  System prompt + RAG context + standalone question
  No conversation history (avoids LLM referencing prior answers over retrieved data)
        ↓
ReadableStream → SvelteKit Response → client reader loop
  Tokens streamed and rendered progressively
```

---

## Data pipeline

**Dagster assets:**

| Asset | Description |
|---|---|
| `fetch_mlb_data` | `@multi_asset` — polls MLB Stats API, writes raw JSON to Supabase (games, players, schedule) |
| `run_dbt_transforms` | `@dbt_assets` — runs `dbt run` + `dbt test` across all 7 models; each model surfaces as an individual asset in Dagster |
| `refresh_embeddings` | `@asset` — depends on 4 analytics tables; re-embeds after transforms complete |

**Schedule:** every 5 days year-round; daily every March at 3:17 AM (staggered to avoid API contention).

**dbt:** 7 models, 50 data tests (PASS=50, WARN=0, ERROR=0). Three-layer structure: sources (raw schema) → staging views → analytics tables.

![Dagster asset graph](assets/dagster-ui.png)

![dbt lineage graph](assets/dbt-lineage.png)

---

## Project structure

```
wbc-dashboard/
├── pipeline/
│   ├── ingestion/
│   │   ├── ingest.py          # MLB Stats API → Supabase raw schema
│   │   └── embed.py           # analytics → sentence engineering → vectors.embeddings
│   ├── dbt/wbc_dbt/
│   │   ├── models/
│   │   │   ├── staging/       # stg_schedule, stg_players, stg_player_game_stats
│   │   │   └── analytics/     # game_results, standings, player_game_stats, player_tournament_stats
│   │   └── macros/            # generate_schema_name (prevents schema doubling)
│   ├── dagster/wbc_dagster/
│   │   └── assets/            # ingestion.py, dbt_assets.py, embeddings.py
│   ├── Dockerfile
│   ├── entrypoint.sh          # generates profiles.yml from env vars at runtime
│   └── docker-compose.yml
└── frontend/
    └── src/
        ├── lib/server/
        │   ├── db.ts          # Supabase server client (service role, analytics schema)
        │   └── rag.ts         # rewriteQuestion → embedQuestion → retrieveContext → queryRagStream
        └── routes/
            ├── +page.svelte              # standings + bracket + recent games
            ├── games/                    # game browser
            ├── players/                  # leaderboards
            ├── players/[id]/             # player profile + game log
            ├── chat/                     # streaming AI chat UI
            └── api/chat/+server.ts       # RAG endpoint
```

---

## CI/CD

**`dbt-tests.yml`** — runs on every push: `dbt deps` → `dbt run` → `dbt test`.

**`deploy-pipeline.yml`** — runs on push to `main` when `pipeline/**` changes. SSHes into EC2: `git pull` → `docker compose down` → `docker compose up --build -d`.

**Vercel** — SvelteKit auto-deploys from `main` via the native adapter.

---

## Local setup

**Prerequisites:** Python 3.11+, Node.js 20+, Docker, dbt-postgres, Supabase project with pgvector enabled, Groq API key (free tier)

```bash
# Pipeline
cd pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python ingestion/ingest.py
cd dbt/wbc_dbt && dbt run && dbt test
python ingestion/embed.py

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173

# Full pipeline (Docker)
cd pipeline && docker compose up --build
# Dagster UI → http://localhost:3000
```

**Environment variables:**

```
DB_HOST, DB_USER, DB_PASSWORD, DB_NAME   # Supabase Postgres
SUPABASE_URL                              # Supabase project URL
SUPABASE_SERVICE_ROLE_KEY                 # Server-only (never exposed to browser)
GROQ_API_KEY                              # Groq free tier
DBT_PROJECT_DIR                           # Absolute path to pipeline/dbt/wbc_dbt
```

---

## Data

All data sourced from the [MLB Stats API](https://statsapi.mlb.com) (free, no auth required). Covers all WBC seasons: ~251 games · ~605 players · ~14,700 player-game records · 16,000+ vector embeddings.

---

MIT License