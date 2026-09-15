"""
Extract text from JLPT PDFs and write chunked JSON to disk.

Airflow-ready:
  - CLI arguments for input/output directories
  - Structured logging
  - Explicit exit codes
  - No hardcoded paths
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("extract")


# ---------- Helpers ----------
def classify_section(text: str) -> str:
    """Rule-based chunk classification (refined later in dbt)."""
    text_lower = text.lower()
    if any(m in text for m in ["〜て", "〜に", "〜が", "〜は", "grammar", "pattern", "structure"]):
        return "grammar"
    if any(m in text_lower for m in ["vocabulary", "vocab", "meaning", "reading", "n3", "n4", "n5"]):
        return "vocabulary"
    if len(text) > 500:
        return "passage"
    return "general"


def extract_text_from_pdf(pdf_path: Path, chunk_size: int = 300) -> list[dict]:
    """Extract chunked text from a single PDF."""
    chunks: list[dict] = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Could not open {pdf_path.name}: {e}")
        return chunks

    logger.info(f"Processing {pdf_path.name} ({len(doc)} pages)")

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if len(text.strip()) < 50:
            logger.debug(f"  Skipping page {page_num + 1} — too little text")
            continue

        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text) < 100:
                continue

            chunks.append({
                "source_file": pdf_path.name,
                "page_number": page_num + 1,
                "chunk_index": i // chunk_size,
                "content": chunk_text,
                "content_length": len(chunk_text),
                "word_count": len(chunk_words),
                "extracted_at": datetime.now().isoformat(),
                "section_type": classify_section(chunk_text),
            })

    doc.close()
    return chunks

def prune_old_outputs(output_dir: Path, keep: int) -> int:
    """
    Keep the N most recent extracted_*.json files, delete older ones.
    Returns count of files deleted. If keep <= 0, does nothing.
    """
    if keep <= 0:
        return 0

    files = sorted(
        output_dir.glob("extracted_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    to_delete = files[keep:]
    for f in to_delete:
        try:
            f.unlink()
            logger.info(f"Pruned old extraction: {f.name}")
        except Exception as e:
            logger.warning(f"Could not delete {f.name}: {e}")
    return len(to_delete)


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(
        description="Extract text from JLPT PDFs and write chunked JSON output."
    )
    parser.add_argument(
        "--input-dir",
        default=str(PROJECT_ROOT / "data" / "raw_pdfs"),
        help="Directory containing source PDFs (default: data/raw_pdfs)."
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "extracted"),
        help="Directory to write extracted JSON (default: data/extracted)."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=300,
        help="Words per chunk (default: 300)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract but don't write output file."
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of most recent extracted JSON files to keep (default: 5). Set 0 to disable cleanup."
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {input_dir}")
        logger.warning("Add JLPT PDF files and re-run.")
        # Not a failure — an empty input dir isn't an error
        sys.exit(0)

    logger.info("=" * 60)
    logger.info(f"Input dir:  {input_dir}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"PDFs found: {len(pdf_files)}")
    logger.info(f"Chunk size: {args.chunk_size}")
    logger.info(f"Dry run:    {args.dry_run}")
    logger.info("=" * 60)

    all_chunks: list[dict] = []
    for pdf_path in pdf_files:
        chunks = extract_text_from_pdf(pdf_path, chunk_size=args.chunk_size)
        logger.info(f"  → {len(chunks)} chunks from {pdf_path.name}")
        all_chunks.extend(chunks)

    logger.info(f"Total chunks extracted: {len(all_chunks)}")

    if args.dry_run:
        logger.info("[dry-run] Skipping file write")
        sys.exit(0)

    if not all_chunks:
        logger.warning("No chunks produced — nothing to write.")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"extracted_{timestamp}.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception(f"Failed to write output: {e}")
        sys.exit(1)

    logger.info(f"Wrote {len(all_chunks)} chunks → {output_file}")
    deleted = prune_old_outputs(output_dir, args.keep)
    if deleted:
        logger.info(f"Pruned {deleted} old extraction file(s)")
    logger.info("✅ extract complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
