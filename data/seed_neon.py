"""
Seed Neon (cloud PostgreSQL) from local PostgreSQL.

Copies: vocabulary, grammar_rules, raw_chunks.
Reads both connection strings from .env:
  - local: DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD
  - neon:  DATABASE_URL
"""

import os
import sys
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("seed_neon")


def get_local_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5434)),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def get_neon_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(url)


def copy_table(local_conn, neon_conn, table, columns):
    """Copy all rows from local table to neon table."""
    logger.info(f"Copying {table}...")

    with local_conn.cursor() as lc:
        lc.execute(f"SELECT {', '.join(columns)} FROM {table}")
        rows = lc.fetchall()
    logger.info(f"  Local rows: {len(rows)}")

    if not rows:
        logger.info(f"  Skipping {table} (empty)")
        return 0

    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

    with neon_conn.cursor() as nc:
        # Truncate first so re-runs are idempotent
        nc.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")
        execute_batch(nc, sql, rows, page_size=500)
    neon_conn.commit()

    logger.info(f"  Inserted into Neon: {len(rows)}")
    return len(rows)


def main():
    logger.info("=" * 60)
    logger.info("Seeding Neon from local PostgreSQL")
    logger.info("=" * 60)

    # Check tables exist on Neon (requires init.sql to have been applied)
    neon = get_neon_conn()
    with neon.cursor() as nc:
        nc.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        neon_tables = [r[0] for r in nc.fetchall()]

    if not neon_tables:
        logger.error("No tables found on Neon.")
        logger.error("You need to apply data/sql/init.sql to Neon first.")
        logger.error("Easiest way: use Neon's SQL editor and paste the contents of data/sql/init.sql.")
        sys.exit(1)

    logger.info(f"Neon tables found: {neon_tables}")

    local = get_local_conn()

    # Copy in dependency order (vocabulary + grammar_rules reference raw_chunks)
    try:
        copy_table(local, neon, "raw_chunks", [
            "source_file", "page_number", "chunk_index", "content",
            "content_length", "word_count", "section_type",
            "extracted_at", "created_at",
        ])
        copy_table(local, neon, "vocabulary", [
            "japanese_word", "reading", "meaning", "example_sentence",
            "jlpt_level", "created_at",
        ])
        copy_table(local, neon, "grammar_rules", [
            "pattern", "explanation", "example_sentence",
            "jlpt_level", "created_at",
        ])
    except Exception as e:
        logger.exception(f"Seed failed: {e}")
        sys.exit(1)
    finally:
        local.close()
        neon.close()

    # Verify
    neon = get_neon_conn()
    with neon.cursor() as nc:
        for t in ("raw_chunks", "vocabulary", "grammar_rules"):
            nc.execute(f"SELECT COUNT(*) FROM {t}")
            logger.info(f"  Neon {t}: {nc.fetchone()[0]}")
    neon.close()

    logger.info("✅ Seed complete")
    sys.exit(0)


if __name__ == "__main__":
    main()