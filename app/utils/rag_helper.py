"""
Cached access to the LangChain RAG chain for the Streamlit app.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@st.cache_resource(show_spinner="Loading RAG chain...")
def _build_chain():
    """Build the RAG chain once per Streamlit session."""
    from ai.rag import build_rag_chain
    return build_rag_chain()


def get_chain():
    """Return (chain, retriever). Third return value (vector_store) is unused in UI."""
    chain, retriever, _vector_store = _build_chain()
    return chain, retriever