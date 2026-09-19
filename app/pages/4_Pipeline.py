"""
Pipeline status page — data health dashboard.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

from utils.db import run_query, get_table_counts

st.set_page_config(page_title="Pipeline — Sakura Stack", page_icon="📊", layout="wide")

st.title("📊 Pipeline Status")
st.caption("Data health and pipeline stats.")

st.subheader("Row counts")
try:
    counts = get_table_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Raw chunks", f"{counts['raw_chunks']:,}")
    c2.metric("Vocabulary", f"{counts['vocabulary']:,}")
    c3.metric("Grammar patterns", f"{counts['grammar_rules']:,}")
    c4.metric("Study items (dbt)", f"{counts['mart_study_items']:,}")
except Exception as e:
    st.error(f"Could not fetch counts: {e}")

st.divider()

st.subheader("Chunks by section type")
try:
    rows = run_query(
        "SELECT section_type, COUNT(*) FROM raw_chunks "
        "GROUP BY section_type ORDER BY COUNT(*) DESC"
    )
    for stype, n in rows:
        st.markdown(f"- **{stype}**: {n:,}")
except Exception as e:
    st.error(f"Query failed: {e}")

st.divider()

st.subheader("Embedding status")
try:
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.HttpClient(host="localhost", port=8000)
    embed_fn = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text",
    )
    collection = client.get_collection(name="jlpt_chunks", embedding_function=embed_fn)
    st.metric("Embedded chunks in ChromaDB", f"{collection.count():,}")
except Exception as e:
    st.warning(f"Could not reach ChromaDB: {e}")

st.divider()

st.subheader("Data dictionary")
st.markdown("""
| Table | Purpose |
|-------|---------|
| `raw_chunks` | Source text chunks for RAG |
| `vocabulary` | Structured N2 vocabulary |
| `grammar_rules` | N2 grammar patterns |
| `mart_study_items` | Unified dbt view (vocab + grammar) |
""")