# ⚾ WBC Dashboard

```{=html}
<p align="center">
```
`<b>`{=html}A full-stack data platform + AI interface for the World
Baseball Classic`</b>`{=html}`<br/>`{=html} `<i>`{=html}Explore baseball
data visually --- or just ask it questions`</i>`{=html}
```{=html}
</p>
```
```{=html}
<p align="center">
```
`<a href="https://wbc.davidr.io">`{=html}`<b>`{=html}🌐 Live
Demo`</b>`{=html}`</a>`{=html} • `<a href="#">`{=html}`<b>`{=html}📦
GitHub`</b>`{=html}`</a>`{=html}
```{=html}
</p>
```

------------------------------------------------------------------------

```{=html}
<p align="center">
```
`<img src="https://img.shields.io/badge/Frontend-SvelteKit-ff3e00?style=for-the-badge&logo=svelte" />`{=html}
`<img src="https://img.shields.io/badge/Database-PostgreSQL-316192?style=for-the-badge&logo=postgresql" />`{=html}
`<img src="https://img.shields.io/badge/Transform-dbt-ff694b?style=for-the-badge" />`{=html}
`<img src="https://img.shields.io/badge/Orchestration-Dagster-5c6ac4?style=for-the-badge" />`{=html}
`<img src="https://img.shields.io/badge/AI-RAG%20%2B%20LLM-black?style=for-the-badge" />`{=html}
```{=html}
</p>
```

------------------------------------------------------------------------

## 🚀 The idea

Most data projects stop here:

> "Here's a dashboard."

This one goes further:

-   📊 **Interactive analytics UI**
-   🧠 **AI that answers questions about your data**
-   ⚙️ **Production-style data pipeline**

👉 It's a **data platform**, not just a frontend.

------------------------------------------------------------------------

## ⚡ Demo

### 📊 Dashboard

```{=html}
<p align="center">
```
`<img src="assets/dashboard.gif" width="800"/>`{=html}
```{=html}
</p>
```
### 💬 AI Chat (RAG)

```{=html}
<p align="center">
```
`<img src="assets/chat.gif" width="800"/>`{=html}
```{=html}
</p>
```

------------------------------------------------------------------------

## 🧠 How the AI works

``` mermaid
graph LR
    A[User Question] --> B[Rewrite Query]
    B --> C[Embedding]
    C --> D[Vector Search]
    D --> E[Context]
    E --> F[LLM Answer]
```

------------------------------------------------------------------------

## 🏗️ Architecture

``` mermaid
graph TD
    A[MLB API] --> B[Postgres]
    B --> C[dbt Models]
    B --> D[pgvector]

    C --> E[Analytics Tables]
    D --> F[Vector Search]

    G[Dagster] --> A
    G --> C
    G --> D

    H[Embeddings Model] --> D
    I[LLM] --> J[RAG]

    F --> J
    K[SvelteKit] --> J
    K --> B
```

------------------------------------------------------------------------

## 🧱 Stack

-   SvelteKit\
-   PostgreSQL (Supabase)\
-   dbt\
-   Dagster\
-   pgvector\
-   all-MiniLM-L6-v2\
-   Groq (Llama 3)\
-   Docker + AWS EC2

------------------------------------------------------------------------

## 📄 License

MIT
