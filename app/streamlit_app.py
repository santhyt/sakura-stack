"""
Sakura Stack — Home page.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

st.set_page_config(
    page_title="Sakura Stack",
    page_icon="🌸",
    layout="wide",
)

from utils.db import get_table_counts

st.title("🌸 Sakura Stack")
st.caption("AI-powered JLPT N2 study assistant — grounded in your own materials")

st.markdown("""
Sakura Stack is an end-to-end data + AI project that:
1. Ingests JLPT study materials
2. Transforms them with dbt
3. Embeds them into a vector store
4. Serves grounded answers via a RAG pipeline
""")

st.divider()

# ---- Quick navigation cards ----
st.subheader("Jump to")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("### 💬 Ask")
        st.caption("Chat with your study materials")
        st.page_link("pages/1_Ask.py", label="Open →", use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown("### 📚 Vocabulary")
        st.caption("Browse N2 vocabulary")
        st.page_link("pages/2_Vocabulary.py", label="Open →", use_container_width=True)

with col3:
    with st.container(border=True):
        st.markdown("### 📖 Grammar")
        st.caption("Browse N2 grammar patterns")
        st.page_link("pages/3_Grammar.py", label="Open →", use_container_width=True)

with col4:
    with st.container(border=True):
        st.markdown("### 📊 Pipeline")
        st.caption("Data health and stats")
        st.page_link("pages/4_Pipeline.py", label="Open →", use_container_width=True)

st.divider()

# ---- Live metrics ----
st.subheader("Live data")

try:
    counts = get_table_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Raw chunks", f"{counts['raw_chunks']:,}")
    c2.metric("Vocabulary", f"{counts['vocabulary']:,}")
    c3.metric("Grammar patterns", f"{counts['grammar_rules']:,}")
    c4.metric("Study items (dbt)", f"{counts['mart_study_items']:,}")
except Exception as e:
    st.error(f"Could not connect to the database. Is Docker running? Details: {e}")

st.divider()
st.caption("Built with PostgreSQL · dbt · ChromaDB · LangChain · Ollama · Streamlit")