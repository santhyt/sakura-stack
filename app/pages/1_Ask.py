"""
Ask page — chat with the RAG system.
"""

import sys
from pathlib import Path

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

st.set_page_config(page_title="Ask — Sakura Stack", page_icon="💬", layout="wide")

st.title("💬 Ask Sakura Stack")
st.caption("Ask about JLPT N2 vocabulary, grammar, or reading comprehension.")

# ---- Ollama availability check ----
OLLAMA_AVAILABLE = False
try:
    r = requests.get("http://localhost:11434/api/tags", timeout=1)
    OLLAMA_AVAILABLE = r.status_code == 200
except Exception:
    OLLAMA_AVAILABLE = False

if not OLLAMA_AVAILABLE:
    st.warning(
        "The Ask feature runs a local LLM (Ollama) and is not available "
        "in this hosted demo. The RAG pipeline runs on my laptop — see "
        "the Loom walkthrough in the README for a live demo.\n\n"
        "**The Vocabulary, Grammar, and Pipeline tabs all work** — they "
        "query this same PostgreSQL database in the cloud."
    )
    st.stop()
# ---- End Ollama check ----

# Import the hybrid query function only when Ollama is available
from ai.rag import query_rag

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Options")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("Sources"):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"**[{i}]** `{src.get('section_type', '?')}` "
                        f"— {src.get('source_file', '?')}"
                    )

if prompt := st.chat_input("e.g. What is the difference between みたい and らしい?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving and generating (this may take a moment)..."):
            try:
                result = query_rag(prompt)
            except Exception as e:
                st.error(f"Generation failed: {e}")
                st.stop()

        st.markdown(result["answer"])

        if result["sources"]:
            with st.expander("Sources"):
                for i, src in enumerate(result["sources"], 1):
                    st.markdown(
                        f"**[{i}]** `{src.get('section_type', '?')}` "
                        f"— {src.get('source_file', '?')}"
                    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })