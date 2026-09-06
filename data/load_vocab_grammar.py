"""
Load only vocabulary and grammar from Replit data.
"""

import json
import os
import psycopg2
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "sakura_stack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "JLPTpassN3!")
    )

def load_vocabulary(conn, vocab_items, level='N2'):
    """Load vocabulary without ON CONFLICT."""
    cursor = conn.cursor()
    inserted = 0
    
    for item in vocab_items:
        try:
            japanese_word = item.get('word', '')
            reading = item.get('reading', '')
            meaning = item.get('meaning', '')
            example_sentence = item.get('exampleJP', '')
            
            if not japanese_word:
                continue
            
            # Check if exists
            cursor.execute(
                "SELECT id FROM vocabulary WHERE japanese_word = %s AND reading = %s",
                (japanese_word, reading)
            )
            if cursor.fetchone():
                continue
            
            cursor.execute("""
                INSERT INTO vocabulary (japanese_word, reading, meaning, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s, %s)
            """, (japanese_word, reading, meaning, example_sentence, level))
            inserted += 1
            
        except Exception as e:
            logger.error(f"Error: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    logger.info(f"Vocabulary: {inserted} inserted")
    return inserted

def load_grammar(conn, grammar_items, level='N2'):
    """Load grammar without ON CONFLICT."""
    cursor = conn.cursor()
    inserted = 0
    
    for item in grammar_items:
        try:
            pattern = item.get('pattern', '')
            explanation = item.get('meaning', '')
            example_sentence = item.get('exampleJP', '')
            
            if not pattern:
                continue
            
            # Check if exists
            cursor.execute(
                "SELECT id FROM grammar_rules WHERE pattern = %s",
                (pattern,)
            )
            if cursor.fetchone():
                continue
            
            cursor.execute("""
                INSERT INTO grammar_rules (pattern, explanation, example_sentence, jlpt_level)
                VALUES (%s, %s, %s, %s)
            """, (pattern, explanation, example_sentence, level))
            inserted += 1
            
        except Exception as e:
            logger.error(f"Error: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    logger.info(f"Grammar: {inserted} inserted")
    return inserted

def main():
    replit_path = r"C:\Users\san78\Downloads\JLPT-Countdown-Planner\JLPT-Countdown-Planner"
    
    try:
        conn = get_db_connection()
        logger.info("✅ Database connected!")
        
        # Load Teacher Data
        teacher_file = Path(replit_path) / 'artifacts' / 'jlpt-n3' / 'src' / 'data' / 'n2TeacherExamData.json'
        if teacher_file.exists():
            with open(teacher_file, 'r', encoding='utf-8') as f:
                teacher_data = json.load(f)
            
            if 'vocab' in teacher_data:
                logger.info(f"Loading {len(teacher_data['vocab'])} vocabulary items...")
                load_vocabulary(conn, teacher_data['vocab'], 'N2')
            
            if 'grammar' in teacher_data:
                logger.info(f"Loading {len(teacher_data['grammar'])} grammar items...")
                load_grammar(conn, teacher_data['grammar'], 'N2')
        
        # Load Kaka Data
        kaka_file = Path(replit_path) / 'artifacts' / 'jlpt-n3' / 'src' / 'data' / 'n2KakaExamData.json'
        if kaka_file.exists():
            with open(kaka_file, 'r', encoding='utf-8') as f:
                kaka_data = json.load(f)
            
            categories = ['verbs', 'adverbs', 'iAdjectives', 'naAdjectives', 
                         'onyomi', 'loanwords', 'readingGrammar', 'listeningGrammar',
                         'conjunctions', 'listeningWords']
            
            for category in categories:
                if category in kaka_data:
                    items = kaka_data[category]
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
                        logger.info(f"Loading {len(vocab_items)} items from {category}...")
                        load_vocabulary(conn, vocab_items, 'N2')
        
        conn.close()
        
        # Show summary
        conn2 = get_db_connection()
        cursor = conn2.cursor()
        cursor.execute("SELECT COUNT(*) FROM vocabulary")
        vocab_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM grammar_rules")
        grammar_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM raw_chunks")
        chunk_count = cursor.fetchone()[0]
        conn2.close()
        
        print("\n" + "=" * 50)
        print("FINAL DATA IMPORT SUMMARY")
        print("=" * 50)
        print(f"Vocabulary items: {vocab_count}")
        print(f"Grammar rules: {grammar_count}")
        print(f"Raw chunks: {chunk_count}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()