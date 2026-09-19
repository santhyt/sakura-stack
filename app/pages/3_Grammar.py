"""
Grammar browse page.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

from utils.db import run_query

st.set_page_config(page_title="Grammar — Sakura Stack", page_icon="📖", layout="wide")

st.title("📖 Grammar")
st.caption("Browse N2 grammar patterns.")

with st.sidebar:
    st.subheader("Filters")
    search = st.text_input("Search (pattern / explanation)")
    level = st.selectbox("JLPT level", ["All", "N2", "N3", "N1", "N4", "N5"])
    limit = st.slider("Max results", 50, 500, 200, step=50)

where = []
params = []
if search:
    where.append("(pattern ILIKE %s OR explanation ILIKE %s)")
    params.extend([f"%{search}%"] * 2)
if level != "All":
    where.append("jlpt_level = %s")
    params.append(level)

sql = "SELECT pattern, explanation, example_sentence, jlpt_level FROM grammar_rules"
if where:
    sql += " WHERE " + " AND ".join(where)
sql += f" ORDER BY pattern LIMIT {limit}"

try:
    rows = run_query(sql, tuple(params))
except Exception as e:
    st.error(f"Query failed: {e}")
    st.stop()

st.caption(f"Showing {len(rows)} pattern(s)")

for pattern, explanation, example, lvl in rows:
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"### {pattern}")
            if lvl:
                st.caption(f"`{lvl}`")
        with col2:
            st.markdown(f"**Meaning:** {explanation or '—'}")
            if example:
                st.markdown(f"**Example:** {example}")