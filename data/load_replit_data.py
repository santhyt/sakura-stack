"""
First attemp (partial success) - keep as documentation of initial approach
working script is load_vocab_grammar.py
The load_replit_data.py script was trying to do everything at once (vocabulary + grammar + raw chunks + Kaka data). It had two problems:

ON CONFLICT errors - tried to use uniqueness constraints that don't exist

Mixed data types - some Kaka data items were strings, not dictionaries

What We Did Instead
The load_vocab_grammar.py script:

Only loads vocabulary and grammar (which was the missing part)

Checked for duplicates manually instead of using ON CONFLICT

Handled different data formats properly

Successfully loaded 1,157 vocabulary + 275 grammar items

What You Have Now
Script	Status	What it loaded
load_replit_data.py	⚠️ Partial success	Loaded 2,445 raw chunks (from earlier run)
load_vocab_grammar.py	✅ Complete success	Loaded 1,157 vocab + 275 grammar


This file was to:
Load Replit JLPT data into Sakura Stack PostgreSQL database.
CORRECTED for actual schema:
- vocabulary: japanese_word, reading, meaning, example_sentence, jlpt_level
- grammar_rules: pattern, explanation, example_sentence, jlpt_level
- raw_chunks: source_file, page_number, chunk_index, content, section_type
"""

import json
import os
import psycopg2
from datetime import datetime
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "JLPTpassN3!")
    )

def load_vocabulary(conn, vocab_items, level='N2'):
    """Load vocabulary - uses japanese_word column."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    for item in vocab_items:
        try:
            japanese_word = item.get('word', '')
            reading = item.get('reading', '')
            meaning = item.get('meaning', '')
            example_sentence = item.get('exampleJP', '')
            
            if not japanese_word:
                skipped += 1
                continue
            
            cursor.execute("""
                INSERT INTO vocabulary (japanese_word, reading, meaning, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (japanese_word, reading) DO NOTHING
            """, (japanese_word, reading, meaning, example_sentence, level))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                
        except Exception as e:
            logger.error(f"Error inserting vocabulary: {e}")
            skipped += 1
    
    conn.commit()
    logger.info(f"Vocabulary: {inserted} inserted, {skipped} skipped")
    return inserted

def load_grammar(conn, grammar_items, level='N2'):
    """Load grammar - uses pattern, explanation, example_sentence."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    
    for item in grammar_items:
        try:
            pattern = item.get('pattern', '')
            explanation = item.get('meaning', '')
            example_sentence = item.get('exampleJP', '')
            
            if not pattern:
                skipped += 1
                continue
            
            cursor.execute("""
                INSERT INTO grammar_rules (pattern, explanation, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (pattern) DO NOTHING
            """, (pattern, explanation, example_sentence, level))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                
        except Exception as e:
            logger.error(f"Error inserting grammar: {e}")
            skipped += 1
    
    conn.commit()
    logger.info(f"Grammar: {inserted} inserted, {skipped} skipped")
    return inserted

def load_raw_chunks(conn, items, source_type, level='N2'):
    """Load items as raw chunks - uses source_file column."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    extracted_at = datetime.now().isoformat()
    
    for idx, item in enumerate(items):
        try:
            # Determine content and section_type based on item type
            if 'word' in item:  # Vocabulary item
                content = f"{item.get('word', '')} ({item.get('reading', '')}) - {item.get('meaning', '')}"
                section_type = 'vocabulary'
            elif 'pattern' in item:  # Grammar item
                content = f"{item.get('pattern', '')}: {item.get('meaning', '')}"
                section_type = 'grammar'
            else:
                skipped += 1
                continue
            
            content_length = len(content)
            word_count = len(content.split())
            
            cursor.execute("""
                INSERT INTO raw_chunks (
                    source_file, page_number, chunk_index, content,
                    content_length, word_count, section_type, extracted_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (source_type, 1, idx, content, content_length, word_count, 
                  section_type, extracted_at))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                
        except Exception as e:
            logger.error(f"Error inserting raw chunk: {e}")
            skipped += 1
    
    conn.commit()
    logger.info(f"Raw chunks from {source_type}: {inserted} inserted, {skipped} skipped")
    return inserted

def load_replit_data(replit_path):
    """Main function to load all Replit data."""
    
    logger.info("Starting Replit data import...")
    
    try:
        # Connect to database
        conn = get_db_connection()
        logger.info("✅ Database connected successfully!")
        
        # Load Teacher Exam Data (n2TeacherExamData.json)
        teacher_file = Path(replit_path) / 'artifacts' / 'jlpt-n3' / 'src' / 'data' / 'n2TeacherExamData.json'
        if teacher_file.exists():
            logger.info(f"Loading teacher data from {teacher_file}")
            with open(teacher_file, 'r', encoding='utf-8') as f:
                teacher_data = json.load(f)
            
            # Load vocabulary
            if 'vocab' in teacher_data:
                logger.info(f"Found {len(teacher_data['vocab'])} vocabulary items")
                load_vocabulary(conn, teacher_data['vocab'], 'N2')
                load_raw_chunks(conn, teacher_data['vocab'], 'replit_teacher_vocab', 'N2')
            
            # Load grammar
            if 'grammar' in teacher_data:
                logger.info(f"Found {len(teacher_data['grammar'])} grammar items")
                load_grammar(conn, teacher_data['grammar'], 'N2')
                load_raw_chunks(conn, teacher_data['grammar'], 'replit_teacher_grammar', 'N2')
        else:
            logger.warning(f"Teacher data file not found: {teacher_file}")
        
        # Load Kaka Exam Data (n2KakaExamData.json)
        kaka_file = Path(replit_path) / 'artifacts' / 'jlpt-n3' / 'src' / 'data' / 'n2KakaExamData.json'
        if kaka_file.exists():
            logger.info(f"Loading Kaka data from {kaka_file}")
            with open(kaka_file, 'r', encoding='utf-8') as f:
                kaka_data = json.load(f)
            
            # Process each category
            categories = ['verbs', 'adverbs', 'iAdjectives', 'naAdjectives', 
                         'onyomi', 'loanwords', 'readingGrammar', 'listeningGrammar',
                         'conjunctions', 'listeningWords']
            
            for category in categories:
                if category in kaka_data:
                    items = kaka_data[category]
                    logger.info(f"Found {len(items)} items in {category}")
                    
                    # Convert to vocabulary format
                    vocab_items = []
                    for item in items:
                        if isinstance(item, dict):
                            vocab_items.append({
                                'word': item.get('word', ''),
                                'reading': item.get('reading', ''),
                                'meaning': item.get('meaning', ''),
                                'exampleJP': item.get('example', ''),
                            })
                        elif isinstance(item, str):
                            vocab_items.append({
                                'word': item,
                                'reading': '',
                                'meaning': '',
                                'exampleJP': '',
                            })
                    
                    if vocab_items:
                        load_vocabulary(conn, vocab_items, 'N2')
                        load_raw_chunks(conn, vocab_items, f'replit_kaka_{category}', 'N2')
        else:
            logger.warning(f"Kaka data file not found: {kaka_file}")
        
        conn.close()
        logger.info("✅ Replit data import complete!")
        
        # Show summary
        show_summary()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

def show_summary():
    """Print summary of loaded data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM vocabulary")
        vocab_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM grammar_rules")
        grammar_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_chunks")
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT section_type, COUNT(*) 
            FROM raw_chunks 
            GROUP BY section_type 
            ORDER BY COUNT(*) DESC
        """)
        section_counts = cursor.fetchall()
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("DATA IMPORT SUMMARY")
        print("=" * 50)
        print(f"Vocabulary items: {vocab_count}")
        print(f"Grammar rules: {grammar_count}")
        print(f"Raw chunks: {chunk_count}")
        print("\nBreakdown by section type:")
        for section, count in section_counts:
            print(f"  {section}: {count}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")

if __name__ == "__main__":
    import sys
    
    replit_path = r"C:\Users\san78\Downloads\JLPT-Countdown-Planner\JLPT-Countdown-Planner"
    if len(sys.argv) > 1:
        replit_path = sys.argv[1]
    
    load_replit_data(replit_path)