"""
Ask page — chat with the RAG system (streaming).
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

# Import the hybrid query function
from ai.rag import query_rag

st.set_page_config(page_title="Ask — Sakura Stack", page_icon="💬", layout="wide")

st.title("💬 Ask Sakura Stack")
st.caption("Ask about JLPT N2 vocabulary, grammar, or reading comprehension.")

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