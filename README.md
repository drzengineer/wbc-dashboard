# ⚾ World Baseball Classic Data Platform + RAG AI Assistant

A production-grade **data engineering + AI system** for exploring World Baseball Classic data through both a modern dashboard and a natural-language interface.

🔗 **Live Demo:** https://wbc.davidr.io

---

## 🚀 TL;DR

This project demonstrates an end-to-end data + AI platform that:

- Builds a complete ELT pipeline (Python → PostgreSQL → dbt → Dagster)
- Implements a **custom RAG pipeline** without frameworks like LangChain
- Uses **pgvector** for high-recall semantic retrieval
- Generates **grounded, streaming LLM responses** in real time
- Deploys across **Vercel (frontend) + AWS EC2 (pipeline)**

👉 Designed to showcase **production-level data engineering + applied AI system design**

---

## 📊 What It Does

An interactive analytics platform for the World Baseball Classic (2006–2026), combining:

- 📈 Structured data exploration (standings, games, player stats)
- 💬 Natural-language querying via an AI chat interface
- ⚙️ A full backend data platform powering both

Users can:

- Browse tournament results and player performance across all WBC years
- Ask questions like:
  - “Who had the best OPS in 2017?”
  - “Which team scored the most runs in the semifinals?”
  - “Compare Shohei Ohtani’s WBC performances”
- Receive **real-time, grounded answers** based strictly on tournament data

#

### 💡 Key Idea

Most dashboards stop at charts.

This project extends that model by:

- Building a **complete data platform** (ingestion → modeling → orchestration)
- Adding a **production-style RAG pipeline**
- Enabling **dual interaction modes**: UI + natural language

👉 The result is a unified **data + AI system**, not just a dashboard

---

## 📈 Results

- ~70% improvement in vector similarity after HNSW + sentence engineering (\~0.39 → ~0.66)
- ~16,000+ embeddings generated locally per run (no API limits)
- Sub-second semantic retrieval using pgvector
- Real-time streaming responses via LLM API
- Fully functional pipeline orchestrated and deployed in production

👉 Demonstrates measurable improvements in retrieval quality, system performance, and cost efficiency

---

## 🏗️ Architecture

![Architecture Diagram](assets/architecture.svg)

#

### Pipeline

Ingest → Transform → Embed → Retrieve → Generate → UI

- **Ingestion:** Python pulls MLB Stats API data into PostgreSQL
- **Transform:** dbt models clean and structure data into analytics tables
- **Orchestration:** Dagster manages pipeline execution and dependencies
- **Embedding:** Local SentenceTransformer generates vector embeddings
- **Retrieval:** pgvector (HNSW) performs high-recall similarity search
- **Generation:** LLM produces grounded responses using retrieved context
- **Frontend:** SvelteKit dashboard + streaming chat interface

![Architecture Diagram](assets/dagster-ui.png)

---

## 🤖 RAG System — How It Works

The system converts user queries into standalone questions, retrieves relevant data via vector search, and generates grounded responses using only retrieved context.

### RAG Flow

```
User Query + Conversation History
↓
Rewrite (LLM, deterministic)
↓
Embed (local model)
↓
Retrieve (pgvector similarity search)
↓
Generate (LLM with retrieved context only)
↓
Stream response to UI
```

#

### Key Components

- 🔄 **Context-aware query rewriting**  
  Resolves follow-ups and ambiguity (e.g., “he” → “Shohei Ohtani”)

- ⚡ **Local embedding pipeline**  
  all-MiniLM-L6-v2 runs on-device — no APIs, no rate limits

- 🔍 **Vector retrieval (pgvector + HNSW)**  
  High-recall similarity search directly inside PostgreSQL

- 🧠 **Grounded LLM generation (streaming)**  
  Final responses use only retrieved data — no hallucinated context

---

## ✨ Why This Matters

This project is designed to reflect how modern data + AI systems are built in production environments.


### 🧠 Real-World Engineering Tradeoffs
- Uses **PostgreSQL + pgvector** instead of separate data warehouse + vector DB  
- Chooses **local embeddings** over paid APIs to reduce cost and dependencies  
- Applies **RAG instead of tool-calling** for static analytical data  

👉 Demonstrates the ability to choose the *right tools for the actual problem and scale*

#

### ⚙️ End-to-End System Ownership
- Data ingestion → modeling → orchestration → API → frontend → deployment
- Fully deployed across cloud infrastructure (Vercel + AWS EC2)

👉 Shows ability to design and ship complete production systems

#

### 🔍 Transparent + Debuggable AI
- No abstraction layers (no LangChain)
- Deterministic query rewriting before retrieval
- Clear separation between retrieval and generation

👉 Every step is inspectable — critical for real-world AI systems

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| **Ingestion** | Python |
| **Database** | PostgreSQL (Supabase) |
| **Vector Search** | pgvector (HNSW index) |
| **Transforms** | dbt |
| **Orchestration** | Dagster |
| **Embeddings** | all-MiniLM-L6-v2 (local) |
| **LLM** | Groq (llama-3.3-70b-versatile) |
| **Frontend + API** | SvelteKit + TypeScript |
| **Styling** | Tailwind CSS v4 |
| **Containerization** | Docker |
| **CI/CD** | GitHub Actions |
| **Deployment** | Vercel (frontend), AWS EC2 (pipeline) |

---

## 🚀 Core Engineering Decisions

### 🧩 Unified Data + Vector System
PostgreSQL + pgvector handles both relational and vector workloads  
→ Eliminates need for Snowflake + Pinecone at this scale

#

### ⚖️ Designed for Realistic Data Scale
Dataset (~50K rows) does not justify distributed systems  
→ Prioritizes simplicity, correctness, and performance

#

### 🧠 Custom RAG Pipeline (No Frameworks)
Built without LangChain  
→ Full control, better debuggability, no unnecessary abstraction

#

### 🔍 HNSW for High-Recall Retrieval
Switched from ivfflat → HNSW  
→ ~70% improvement in similarity scores (\~0.39 → ~0.66)

#

### ⚡ Local, Zero-Cost Embeddings
all-MiniLM-L6-v2 runs on CPU  
→ No API costs, no rate limits, fast batch processing (~16K rows/run)

#

### 🛠️ Modern Data Stack (dbt + Dagster)
- dbt for SQL transformations and testing  
- Dagster for asset-based orchestration and lineage  

→ Clean, maintainable, production-ready pipelines

#

### 🔄 ELT Architecture
Raw data stored untransformed; dbt handles modeling  
→ Clear separation of concerns and reproducibility

#

### 🧠 Sentence-Engineered Embeddings
Structured data converted into natural-language sentences + Q&A pairs  
→ Improves retrieval quality significantly (~0.4 → 0.7+)

#

### ⚡ RAG Over Tool-Calling
Pre-indexed embeddings outperform tool-calling for static datasets  
→ Lower latency, simpler architecture, more reliable responses

---

## 🛠️ Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/wbc-dashboard.git
cd wbc-dashboard
```

### 2. Start the pipeline (Docker)

```
cd pipeline
docker compose up --build
```
### 3. Run ingestion + transforms

```
# inside container or local venv
python ingestion/ingest.py
dbt run
dbt test
```

### 4. Generate embeddings

```
python ingestion/embed.py
```

### 5. Start frontend

```
cd ../frontend
npm install
npm run dev
```
### 6. Environment Variables

```
Create .env files for:

Supabase credentials
Groq API key
```

### 👉 Full pipeline + frontend should now be running locally

---

## 📁 Project Structure

```
wbc-dashboard/
├── pipeline/
│   ├── ingestion/               # MLB Stats API extraction + vector embeddings
│   ├── dbt/
│   │   └── wbc_dbt/
│   │       ├── staging/         # Source standardization, type safety, 1:1 raw landing
│   │       ├── intermediate/    # Business logic consolidation, deduplication, joins
│   │       └── mart/            # Kimball dimensional model (dimensions + facts)
│   ├── dagster/                 # Asset orchestration, lineage, and scheduling
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/              # Pages (dashboard, games, players, chat)
│   │   └── lib/server/          # RAG pipeline + database client
├── .github/workflows/           # CI/CD pipelines
├── assets/                      # Architecture diagrams & documentation
└── README.md
```

> ✅ Pipeline follows **standard modern data engineering best practices** with clear separation of concerns across all layers. Each layer has single responsibility, idempotent runs, and built in testing.
---
## 🎯 What This Project Demonstrates

- End-to-end data engineering pipeline design (ELT, dbt, orchestration)
- Practical RAG implementation without frameworks
- Real-world system design tradeoffs and tool selection
- Vector search and semantic retrieval using pgvector
- Deployment of a full-stack + AI system in production

---

## 📌 Summary

This project reflects the ability to:

- Design scalable data systems
- Build and deploy applied AI pipelines
- Make pragmatic engineering decisions based on real constraints

👉 Built to demonstrate readiness for **data engineering and applied AI roles**
