"""
Vocabulary browse page.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

from utils.db import run_query

st.set_page_config(page_title="Vocabulary — Sakura Stack", page_icon="📚", layout="wide")

st.title("📚 Vocabulary")
st.caption("Browse N2 vocabulary extracted from study materials.")

with st.sidebar:
    st.subheader("Filters")
    search = st.text_input("Search (Japanese / reading / meaning)")
    level = st.selectbox("JLPT level", ["All", "N2", "N3", "N1", "N4", "N5"])
    limit = st.slider("Max results", 50, 1000, 200, step=50)

where = []
params = []
if search:
    where.append("(japanese_word ILIKE %s OR reading ILIKE %s OR meaning ILIKE %s)")
    params.extend([f"%{search}%"] * 3)
if level != "All":
    where.append("jlpt_level = %s")
    params.append(level)

sql = "SELECT japanese_word, reading, meaning, example_sentence, jlpt_level FROM vocabulary"
if where:
    sql += " WHERE " + " AND ".join(where)
sql += f" ORDER BY japanese_word LIMIT {limit}"

try:
    rows = run_query(sql, tuple(params))
except Exception as e:
    st.error(f"Query failed: {e}")
    st.stop()

st.caption(f"Showing {len(rows)} item(s)")

for word, reading, meaning, example, lvl in rows:
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"### {word}")
            if reading:
                st.caption(reading)
            if lvl:
                st.caption(f"`{lvl}`")
        with col2:
            st.markdown(f"**Meaning:** {meaning or '—'}")
            if example:
                st.markdown(f"**Example:** {example}")