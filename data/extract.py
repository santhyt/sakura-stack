import json
import os
from datetime import datetime
from pathlib import Path

import fitz  # "fitz" is import name for PyMuPDF
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define where the PDFs live and where extracted output goes
RAW_PDF_DIR = Path("data/raw_pdfs")
OUTPUT_DIR = Path("data/extracted")

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Opens a PDF and extracts text page by page.
    Returns a list of chunks — each chunk is a dict with metadata.
    """
    chunks = []

    # Open the PDF with PyMuPDF
    doc = fitz.open(pdf_path)

    print(f"Processing: {pdf_path.name} ({len(doc)} pages)")

    for page_num, page in enumerate(doc):
        # Extract all text from this page
        text = page.get_text()

        # Skip pages with very little text (likely images or blank pages)
        if len(text.strip()) < 50:
            print(f"  Skipping page {page_num + 1} — too little text")
            continue

        # Split page text into smaller chunks (about 300 words each)
        # Important for RAG — smaller chunks = more precise retrieval
        words = text.split()
        chunk_size = 300

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)

            # Skip if chunk is too short to be useful
            if len(chunk_text) < 100:
                continue

            # Build the chunk record with all metadata
            chunk = {
                "source_file": pdf_path.name,
                "page_number": page_num + 1,
                "chunk_index": i // chunk_size,
                "content": chunk_text,
                "content_length": len(chunk_text),
                "word_count": len(chunk_words),
                "extracted_at": datetime.now().isoformat(),
                # will classify content type properly with dbt later
                # For now, make a simple guess based on content keywords
                "section_type": classify_section(chunk_text),
            }

            chunks.append(chunk)

    doc.close()
    return chunks


def classify_section(text: str) -> str:
    """
    Simple rule-based classification of chunk content type.
    will improve this with proper dbt models later.
    """
    text_lower = text.lower()

    # Japanese grammar patterns tend to have these markers
    if any(
        marker in text
        for marker in ["〜て", "〜に", "〜が", "〜は", "grammar", "pattern", "structure"]
    ):
        return "grammar"

    # Vocabulary sections often have this structure
    if any(
        marker in text_lower
        for marker in ["vocabulary", "vocab", "meaning", "reading", "n3", "n4", "n5"]
    ):
        return "vocabulary"

    # Reading passages are longer flowing text
    if len(text) > 500:
        return "passage"

    # Default
    return "general"


def process_all_pdfs():
    """
    Main function — processes every PDF in the raw_pdfs folder.
    """
    # Find all PDF files
    pdf_files = list(RAW_PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {RAW_PDF_DIR}")
        print("Add some JLPT PDF files to data/raw_pdfs/ and run again")
        return

    print(f"Found {len(pdf_files)} PDF(s) to process")
    print("=" * 50)

    all_chunks = []

    for pdf_path in pdf_files:
        chunks = extract_text_from_pdf(pdf_path)
        all_chunks.extend(chunks)
        print(f"  → Extracted {len(chunks)} chunks from {pdf_path.name}")

    print("=" * 50)
    print(f"Total chunks extracted: {len(all_chunks)}")

    # Save to JSON for now (will load to PostgreSQL in the next step)
    output_file = OUTPUT_DIR / f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {output_file}")

    # Print a sample chunk to see what the output looks like
    if all_chunks:
        print("\nSample chunk:")
        print(json.dumps(all_chunks[0], ensure_ascii=False, indent=2))

    return all_chunks


if __name__ == "__main__":
    process_all_pdfs()
