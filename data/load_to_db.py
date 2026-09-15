"""
Load extracted JSON chunks into the raw_chunks table in PostgreSQL.

Airflow-ready:
  - CLI arguments (which file to load, source override)
  - Structured logging
  - Explicit exit codes
  - Idempotent (skips duplicates via unique index)
"""

import argparse
import glob
import json
import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("load_to_db")


# ---------- Database ----------
def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 5434)),
            dbname=os.getenv("DB_NAME", "sakura_stack"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )
    except psycopg2.OperationalError as e:
        logger.error(
            f"Could not connect to PostgreSQL at "
            f"{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', 5434)}"
        )
        logger.error("Is Docker running? Try: docker-compose up -d")
        raise


# ---------- Loader ----------
def load_chunks_to_db(chunks: list[dict]) -> tuple[int, int]:
    """Insert chunks, skipping duplicates. Returns (inserted, skipped)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    for chunk in chunks:
        try:
            cursor.execute(
                """
                INSERT INTO raw_chunks
                    (source_file, page_number, chunk_index, content,
                     content_length, word_count, section_type, extracted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    chunk["source_file"],
                    chunk["page_number"],
                    chunk["chunk_index"],
                    chunk["content"],
                    chunk["content_length"],
                    chunk["word_count"],
                    chunk["section_type"],
                    chunk["extracted_at"],
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            conn.rollback()
            skipped += 1

    conn.commit()
    cursor.close()
    conn.close()
    return inserted, skipped


def find_latest_extracted(output_dir: Path) -> Path | None:
    """Return the newest extracted_*.json file, or None."""
    files = sorted(output_dir.glob("extracted_*.json"),
                   key=lambda p: p.stat().st_mtime,
                   reverse=True)
    return files[0] if files else None


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(
        description="Load extracted JSON chunks into the PostgreSQL raw_chunks table."
    )
    parser.add_argument(
        "--extracted-file",
        default=None,
        help="Path to a specific extracted JSON. Defaults to the newest in --input-dir."
    )
    parser.add_argument(
        "--input-dir",
        default=str(PROJECT_ROOT / "data" / "extracted"),
        help="Directory to search for the newest extracted JSON (default: data/extracted)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count but don't write to the database."
    )
    args = parser.parse_args()

    # Resolve input file
    if args.extracted_file:
        source = Path(args.extracted_file)
        if not source.exists():
            logger.error(f"Specified file not found: {source}")
            sys.exit(1)
    else:
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            sys.exit(1)
        source = find_latest_extracted(input_dir)
        if source is None:
            logger.error(f"No extracted_*.json files found in {input_dir}")
            logger.error("Run extract.py first.")
            sys.exit(1)

    logger.info("=" * 60)
    logger.info(f"Source file: {source}")
    logger.info(f"Dry run:     {args.dry_run}")
    logger.info("=" * 60)

    # Read JSON
    try:
        with open(source, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except Exception as e:
        logger.exception(f"Failed to read JSON: {e}")
        sys.exit(1)

    logger.info(f"Loaded {len(chunks)} chunks from file")

    if args.dry_run:
        # Count by section_type
        by_type: dict[str, int] = {}
        for c in chunks:
            by_type[c.get("section_type", "unknown")] = by_type.get(c.get("section_type", "unknown"), 0) + 1
        for st, n in sorted(by_type.items()):
            logger.info(f"  [dry-run] {st}: {n}")
        logger.info("[dry-run] Skipping database write")
        sys.exit(0)

    # Insert
    try:
        inserted, skipped = load_chunks_to_db(chunks)
    except Exception as e:
        logger.exception(f"Load failed: {e}")
        sys.exit(1)

    logger.info(f"Inserted: {inserted}, skipped (dupes): {skipped}")

    # Verify counts
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT section_type, COUNT(*) FROM raw_chunks "
            "GROUP BY section_type ORDER BY COUNT(*) DESC"
        )
        rows = cursor.fetchall()
        logger.info("Chunks in database by section type:")
        for st, n in rows:
            logger.info(f"  {st}: {n}")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not verify counts: {e}")

    logger.info("✅ load_to_db complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
