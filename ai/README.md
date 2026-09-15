# AI Layer — RAG (ChromaDB + Ollama)

This layer turns the processed JLPT data into a grounded question-answering
system. It does **not** call any external AI APIs — everything runs locally.

---

## Components

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| Embedding model | Turn text chunks into vectors | `nomic-embed-text` via Ollama |
| Vector store | Store and search embeddings | ChromaDB (Docker, port 8000) |
| LLM | Generate grounded answers | `mistral` 7B via Ollama |
| RAG orchestration | Retrieve → prompt → answer | `rag.py` (direct SDK calls) |

---

## How it works

1. **`embed.py`** — Reads `raw_chunks` from PostgreSQL (2,405 rows), sends
   each to Ollama's embedding endpoint, stores the vectors in ChromaDB.

2. **`rag.py`** — Takes a user question, embeds it with the same model,
   queries ChromaDB for the top-K most similar chunks, builds a grounded
   prompt with numbered context, and sends it to Mistral.

3. **Response** — Returns the answer plus the source chunks used.

### Why not LangChain?

LangChain was in the original plan, but direct SDK calls proved simpler:
- Fewer dependencies
- Retrieval logic is fully visible (important for a portfolio project)
- Easier to debug

---

## Files

| File | Purpose |
|------|---------|
| `embed.py` | Populates ChromaDB from PostgreSQL |
| `rag.py` | Query interface (single question or interactive) |
| `chroma_db/` | *Not used* — ChromaDB runs in Docker, data lives in a Docker volume |

---

## Usage

### Embed chunks (first time or after new data is loaded)
```bash
python ai/embed.py
