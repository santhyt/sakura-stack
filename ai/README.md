# AI Layer — RAG (ChromaDB + Ollama + LangChain)

This layer turns processed JLPT data into a grounded question-answering
system. It runs entirely locally — no external AI APIs required.

---

## Components

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| Embedding model | Turn text chunks into vectors | `nomic-embed-text` via Ollama |
| Vector store | Store and search embeddings | ChromaDB (Docker, port 8000) |
| LLM | Generate grounded answers | `mistral` 7B via Ollama |
| RAG orchestration | Retrieve → prompt → answer | LangChain (`langchain-chroma`, `langchain-ollama`) |
| Hybrid retrieval | Keyword + vector merge | Regex → SQL pre-filter, keyword ranked first |

---

## How it works

1. **`embed.py`** — Reads `raw_chunks` from PostgreSQL (2,885 rows
   embedded to date), sends each to Ollama's embedding endpoint, stores
   the vectors in ChromaDB.

2. **`rag.py`** — Takes a user question and runs **hybrid retrieval**:
   1. Regex-extract Japanese tokens from the question
   2. Direct SQL lookup on `vocabulary` and `grammar_rules` (exact/near match)
   3. Vector search on ChromaDB
   4. Merge results — keyword matches first, then vector — and dedupe
   Then builds a grounded prompt with numbered context and sends it to
   Mistral via LangChain.

3. **Response** — Returns the answer plus the source chunks used.

### Why LangChain?

LangChain gives a provider-agnostic LLM interface (`ChatOllama` ↔
`AzureChatOpenAI`), LCEL-composable chains (`prompt | llm | parser`),
and a vector store abstraction (`langchain-chroma`). Swapping to Azure
OpenAI post-MVP is a two-line change in `rag.py`.

### Hybrid retrieval (post-MVP improvement)

Pure vector search returned semantically similar chunks, not exact
matches. For example, asking *"What does 扱う mean?"* retrieved similar
verbs (従う, 奪う) instead of the 扱う entry itself, and Mistral then
hallucinated the reading as *かんう*.

The fix (in `query_rag`):
- Keyword lookup runs first (regex → SQL on `vocabulary` + `grammar_rules`)
- Vector search runs second
- Results merged with keyword matches ranked ahead
- Prompt forbids inventing readings/meanings

Result: exact lookups now rank the correct entry first.

---

## Files

| File | Purpose |
|------|---------|
| `embed.py` | Populates ChromaDB from PostgreSQL (idempotent, resumable) |
| `rag.py` | Hybrid retrieval + LangChain chain; CLI and interactive modes |
| `chroma_db/` | *Not used* — ChromaDB runs in Docker, data lives in a Docker volume |

---

## Usage

### Embed chunks (first time or after new data is loaded)

```bash
python ai/embed.py
```

- Idempotent — skips chunks already embedded
- Batches of 10 to avoid Ollama timeouts
- Resumes safely after any failure

### Ask a single question

```bash
python ai/rag.py "What does 扱う mean?"
```

### Interactive mode

```bash
python ai/rag.py
```

---

## Configuration

Read from `.env` at the project root:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `DB_PORT` | `5434` | PostgreSQL host port (Docker; avoids WSL2 conflict) |
| `DB_NAME` | `sakura_stack` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | *(required)* | Database password |
| `LLM_MODEL` | `mistral` | Ollama model for generation |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `CHROMA_COLLECTION` | `jlpt_chunks` | Collection name |
| `RAG_TOP_K` | `5` | Number of chunks to retrieve |

---

## Known Limitations & Next Steps

| Limitation | Status / Planned Fix |
|------------|----------------------|
| Retrieval returned semantically similar items instead of exact matches | **Partially fixed** — hybrid retrieval: keyword lookup runs first, then vector search |
| Mistral occasionally hallucinates when context is weak | **Applied** — stricter prompt: "If the context doesn't answer, say so" |
| Grammar patterns that overlap with vocab (みたい, らしい) still mix section types | Filter ChromaDB by `section_type` based on question intent (Phase 5) |
| Single-turn only (no conversational memory) | Add session state in the Streamlit layer |
| First query is slow (~1–2 min on local Ollama) | Model loads into RAM on first call; add warm-up |
| No cross-encoder reranking | Phase 5 |
| Azure OpenAI backend not yet wired | LangChain swap — 2-line change when ready |
| Duplicate chunks from re-running `extract.py` + `load_to_db.py` | Dedupe by `(source_file, page_number, chunk_index)` in Phase 5 |

---

## Requirements

- Ollama running locally (`ollama serve`)
- Models pulled: `mistral`, `nomic-embed-text`
- ChromaDB container on port 8000
- PostgreSQL container with embedded chunks
- Python deps: `chromadb`, `langchain`, `langchain-chroma`, `langchain-ollama`, `ollama`, `psycopg2-binary`, `python-dotenv`