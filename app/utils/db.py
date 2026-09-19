"""
Shared database helper for the Streamlit app.
"""

import os
from pathlib import Path

import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@st.cache_resource
def get_db_connection():
    """Cached DB connection (created once per Streamlit session)."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5434)),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def run_query(sql: str, params: tuple = None) -> list[tuple]:
    """Run a query and return all rows."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    except Exception:
        conn.rollback()
        raise


def get_table_counts() -> dict:
    """Quick row counts for the home + pipeline pages."""
    counts = {}
    for table in ("raw_chunks", "vocabulary", "grammar_rules"):
        rows = run_query(f"SELECT COUNT(*) FROM {table}")
        counts[table] = rows[0][0]
    try:
        rows = run_query("SELECT COUNT(*) FROM mart_study_items")
        counts["mart_study_items"] = rows[0][0]
    except Exception:
        counts["mart_study_items"] = 0
    return counts