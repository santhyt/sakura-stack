"""
Shared database helper for the Streamlit app.

Uses Streamlit's st.connection with Neon (cloud) and fallback to local DB.
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Return a Streamlit SQL connection (Neon cloud or local Docker)."""
    # In cloud: uses .streamlit/secrets.toml [connections.neon]
    # Locally: also uses secrets.toml if present
    try:
        return st.connection("neon", type="sql")
    except Exception:
        # Fallback: local Docker Postgres via psycopg2
        import psycopg2
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 5434)),
            dbname=os.getenv("DB_NAME", "sakura_stack"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )


def run_query(sql: str, params: tuple = None):
    """Run a query and return all rows."""
    conn = get_db_connection()
    if hasattr(conn, "query"):
        # st.connection SQL
        df = conn.query(sql, params=params, ttl="10m")
        return [tuple(row) for row in df.itertuples(index=False)]
    else:
        # psycopg2 fallback
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def get_table_counts() -> dict:
    """Quick row counts."""
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