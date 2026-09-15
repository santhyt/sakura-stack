"""
Load vocabulary and grammar from a Replit export into PostgreSQL.

Airflow-ready:
  - CLI arguments via argparse
  - Structured logging (captured by Airflow UI)
  - Explicit exit codes (0 = success, 1 = failure)
  - Idempotent (skips existing rows)
  - No hardcoded paths
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load .env from project root regardless of cwd (works under Airflow)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("load_vocab_grammar")


# ---------- Database ----------
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 5434)),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ---------- Loaders ----------
def load_vocabulary(conn, vocab_items, level="N2"):
    """Insert vocabulary items that don't already exist. Returns count."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    for item in vocab_items:
        try:
            japanese_word = item.get("word", "") or item.get("japanese_word", "")
            reading = item.get("reading", "")
            meaning = item.get("meaning", "")
            example_sentence = item.get("exampleJP", "") or item.get("example", "")

            if not japanese_word:
                skipped += 1
                continue

            cursor.execute(
                "SELECT id FROM vocabulary WHERE japanese_word = %s AND reading = %s",
                (japanese_word, reading)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute(
                """
                INSERT INTO vocabulary
                    (japanese_word, reading, meaning, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (japanese_word, reading, meaning, example_sentence, level)
            )
            inserted += 1

        except Exception as e:
            logger.error(f"Vocabulary insert failed: {e}")
            conn.rollback()
            skipped += 1

    conn.commit()
    logger.info(f"Vocabulary — inserted: {inserted}, skipped: {skipped}")
    return inserted


def load_grammar(conn, grammar_items, level="N2"):
    """Insert grammar rules that don't already exist. Returns count."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    for item in grammar_items:
        try:
            pattern = item.get("pattern", "")
            explanation = item.get("meaning", "") or item.get("explanation", "")
            example_sentence = item.get("exampleJP", "") or item.get("example_sentence", "")

            if not pattern:
                skipped += 1
                continue

            cursor.execute(
                "SELECT id FROM grammar_rules WHERE pattern = %s", (pattern,)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute(
                """
                INSERT INTO grammar_rules
                    (pattern, explanation, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s)
                """,
                (pattern, explanation, example_sentence, level)
            )
            inserted += 1

        except Exception as e:
            logger.error(f"Grammar insert failed: {e}")
            conn.rollback()
            skipped += 1

    conn.commit()
    logger.info(f"Grammar — inserted: {inserted}, skipped: {skipped}")
    return inserted


# ---------- Source file handlers ----------
def load_teacher_file(conn, path: Path, level: str):
    logger.info(f"Reading teacher file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "vocab" in data:
        logger.info(f"Found {len(data['vocab'])} vocabulary entries")
        load_vocabulary(conn, data["vocab"], level)

    if "grammar" in data:
        logger.info(f"Found {len(data['grammar'])} grammar entries")
        load_grammar(conn, data["grammar"], level)


def load_kaka_file(conn, path: Path, level: str):
    logger.info(f"Reading kaka file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        kaka_data = json.load(f)

    categories = [
        "verbs", "adverbs", "iAdjectives", "naAdjectives",
        "onyomi", "loanwords", "readingGrammar", "listeningGrammar",
        "conjunctions", "listeningWords",
    ]

    for category in categories:
        if category not in kaka_data:
            continue
        raw_items = kaka_data[category]
        vocab_items = []
        for item in raw_items:
            if isinstance(item, dict):
                vocab_items.append({
                    "word": item.get("word", ""),
                    "reading": item.get("reading", ""),
                    "meaning": item.get("meaning", ""),
                    "exampleJP": item.get("example", ""),
                })
            elif isinstance(item, str):
                vocab_items.append({
                    "word": item, "reading": "", "meaning": "", "exampleJP": ""
                })
        if vocab_items:
            logger.info(f"Category '{category}': {len(vocab_items)} items")
            load_vocabulary(conn, vocab_items, level)


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(
        description="Load JLPT vocabulary and grammar from a Replit export into PostgreSQL."
    )
    parser.add_argument(
        "--source-dir",
        default=r"C:\Users\san78\Downloads\JLPT-Countdown-Planner\JLPT-Countdown-Planner",
        help="Path to the Replit export root directory."
    )
    parser.add_argument(
        "--level",
        default="N2",
        help="JLPT level to tag loaded items with (default: N2)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files and log counts without writing to the database."
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Sakura Stack — vocabulary/grammar loader")
    logger.info(f"Source dir: {source_dir}")
    logger.info(f"JLPT level: {args.level}")
    logger.info(f"Dry run:    {args.dry_run}")
    logger.info("=" * 60)

    # Locate expected files
    teacher_file = source_dir / "artifacts" / "jlpt-n3" / "src" / "data" / "n2TeacherExamData.json"
    kaka_file = source_dir / "artifacts" / "jlpt-n3" / "src" / "data" / "n2KakaExamData.json"

    if not teacher_file.exists() and not kaka_file.exists():
        logger.error("Neither teacher nor kaka file found. Aborting.")
        sys.exit(1)

    # Connect (unless dry-run)
    conn = None
    if not args.dry_run:
        try:
            conn = get_db_connection()
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)

    try:
        if teacher_file.exists():
            if args.dry_run:
                with open(teacher_file, encoding="utf-8") as f:
                    d = json.load(f)
                logger.info(f"[dry-run] teacher vocab={len(d.get('vocab', []))}, grammar={len(d.get('grammar', []))}")
            else:
                load_teacher_file(conn, teacher_file, args.level)
        else:
            logger.warning(f"Teacher file not found: {teacher_file}")

        if kaka_file.exists():
            if args.dry_run:
                with open(kaka_file, encoding="utf-8") as f:
                    d = json.load(f)
                total = sum(len(v) for v in d.values() if isinstance(v, list))
                logger.info(f"[dry-run] kaka total items={total}")
            else:
                load_kaka_file(conn, kaka_file, args.level)
        else:
            logger.warning(f"Kaka file not found: {kaka_file}")

        # Summary
        if conn is not None:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vocabulary")
            v = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM grammar_rules")
            g = cur.fetchone()[0]
            logger.info(f"Final counts — vocabulary: {v}, grammar: {g}")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        if conn is not None:
            conn.close()
        sys.exit(1)

    if conn is not None:
        conn.close()

    logger.info("✅ load_vocab_grammar complete")
    sys.exit(0)


if __name__ == "__main__":
    main()