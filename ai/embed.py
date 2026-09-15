"""
Embed raw_chunks into ChromaDB for the RAG system.
Connects to ChromaDB running in Docker.
"""

import os
from pathlib import Path
import psycopg2
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import logging

# Load .env from project root explicitly
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_connection():
    """Connect to PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", 5434),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )


def embed_chunks():
    """Embed all raw chunks into ChromaDB."""

    logger.info(f"DB config: host={os.getenv('DB_HOST')}, port={os.getenv('DB_PORT')}, user={os.getenv('DB_USER')}, db={os.getenv('DB_NAME')}")

    # Connect to ChromaDB (Docker container)
    chroma_client = chromadb.HttpClient(
        host="localhost",
        port=8000,
        settings=chromadb.Settings(
            chroma_client_auth_provider=None,
            anonymized_telemetry=False,
        )
    )
    logger.info("✅ Connected to ChromaDB")

    # Use Ollama for embeddings with extended timeout
    embed_fn = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text"
    )

    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name="jlpt_chunks",
        embedding_function=embed_fn
    )
    existing_count = collection.count()
    logger.info(f"Collection 'jlpt_chunks' ready. Current count: {existing_count}")

    # Get chunks from PostgreSQL
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, content, section_type, source_file
        FROM raw_chunks
        WHERE content IS NOT NULL AND LENGTH(content) > 10
        ORDER BY id
    """)
    chunks = cursor.fetchall()
    conn.close()

    logger.info(f"Found {len(chunks)} chunks in PostgreSQL")

    # Get already-embedded IDs to support resume
    existing_ids = set()
    if existing_count > 0:
        # Fetch existing IDs in batches
        offset = 0
        while True:
            result = collection.get(limit=1000, offset=offset, include=[])
            if not result['ids']:
                break
            existing_ids.update(result['ids'])
            offset += 1000
            if len(result['ids']) < 1000:
                break
        logger.info(f"Already embedded: {len(existing_ids)} chunks")

    # Filter out already embedded chunks
    new_chunks = [c for c in chunks if f"chunk_{c[0]}" not in existing_ids]
    logger.info(f"New chunks to embed: {len(new_chunks)}")

    if not new_chunks:
        logger.info("✅ All chunks already embedded!")
        return

    # Small batches to avoid timeout
    batch_size = 10
    total = len(new_chunks)

    for i in range(0, total, batch_size):
        batch = new_chunks[i:i + batch_size]
        ids = [f"chunk_{row[0]}" for row in batch]
        contents = [row[1] for row in batch]
        metadatas = [
            {"section_type": row[2] or "general", "source_file": row[3] or "unknown"}
            for row in batch
        ]

        try:
            collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )
            logger.info(f"Embedded {min(i + batch_size, total)}/{total} new chunks (total in collection: {collection.count()})")
        except Exception as e:
            logger.error(f"Error at batch {i}: {e}")
            logger.info(f"Progress saved. Re-run the script to resume from chunk {i}.")
            break

    logger.info(f"✅ Done! Collection now has {collection.count()} documents")


if __name__ == "__main__":
    embed_chunks()