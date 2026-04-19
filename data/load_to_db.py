import json
import os
from glob import glob
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_chunks_to_db(chunks: list[dict]):
    """Load extracted chunks into the raw_chunks table."""
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
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s)
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
            inserted += 1
        except Exception as e:
            print(f"Error inserting chunk: {e}")
            skipped += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Loaded {inserted} chunks into database ({skipped} skipped)")


def main():
    # Find the most recent extracted JSON file
    extracted_files = sorted(glob("data/extracted/*.json"))

    if not extracted_files:
        print("No extracted files found. Run extract.py first.")
        return

    latest_file = extracted_files[-1]
    print(f"Loading from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Found {len(chunks)} chunks to load")
    load_chunks_to_db(chunks)

    # Quick verification query
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT section_type, COUNT(*) FROM raw_chunks GROUP BY section_type")
    results = cursor.fetchall()
    print("\nChunks in database by type:")
    for row in results:
        print(f"  {row[0]}: {row[1]} chunks")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
