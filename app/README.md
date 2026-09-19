# App Layer — Streamlit UI

Multi-page Streamlit application serving the RAG pipeline.

## Pages

| Page | Purpose |
|------|---------|
| Home | Overview + quick metrics + navigation cards |
| 💬 Ask | Chat with the hybrid RAG pipeline |
| 📚 Vocabulary | Browse / search N2 vocabulary |
| 📖 Grammar | Browse / search N2 grammar patterns |
| 📊 Pipeline | Row counts, section breakdowns, embedding status |

## Structure

```
app/
├── streamlit_app.py       # Home
├── pages/
│   ├── 1_Ask.py
│   ├── 2_Vocabulary.py
│   ├── 3_Grammar.py
│   └── 4_Pipeline.py
└── utils/
    ├── db.py              # Shared DB helper
    └── rag_helper.py      # Cached RAG chain
```

## Run locally

```bash
# Make sure Docker containers are running
docker-compose up -d

# Then launch Streamlit
streamlit run app/streamlit_app.py
```

Opens at http://localhost:8501

## Dependencies

Requires `ai/embed.py` to have been run at least once (so ChromaDB has
embedded chunks) and Ollama to be running (for embeddings + LLM).

## Configuration

Reads from `.env` at project root.

## Hybrid retrieval note

The Ask page calls `ai.rag.query_rag()`, which performs hybrid retrieval:

1. Regex-extract Japanese tokens from the question
2. Direct SQL lookup on `vocabulary` and `grammar_rules`
3. Vector search on ChromaDB
4. Merge (keyword first, then vector) and dedupe

This is why the UI no longer uses `retriever.invoke()` directly — doing
so would bypass the keyword pre-filter.

## Why no token streaming (yet)

`query_rag()` returns the full answer after generation completes, so the
UI shows a spinner instead of streaming tokens. Streaming can be added
back by exposing a streaming variant of `query_rag` later.