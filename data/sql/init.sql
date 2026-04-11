-- Raw chunks table — everything extracted from PDFs lands here first
CREATE TABLE IF NOT EXISTS raw_chunks (
    id SERIAL PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    content TEXT NOT NULL,
    content_length INTEGER,
    word_count INTEGER,
    section_type VARCHAR(50),
    extracted_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vocabulary table — populated by dbt from raw_chunks
CREATE TABLE IF NOT EXISTS vocabulary (
    id SERIAL PRIMARY KEY,
    japanese_word VARCHAR(100),
    reading VARCHAR(100),
    meaning TEXT,
    jlpt_level VARCHAR(5),
    example_sentence TEXT,
    source_chunk_id INTEGER REFERENCES raw_chunks(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Grammar rules table — populated by dbt
CREATE TABLE IF NOT EXISTS grammar_rules (
    id SERIAL PRIMARY KEY,
    pattern VARCHAR(200),
    explanation TEXT,
    example_sentence TEXT,
    jlpt_level VARCHAR(5),
    source_chunk_id INTEGER REFERENCES raw_chunks(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Passages table — reading comprehension texts
CREATE TABLE IF NOT EXISTS passages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    jlpt_level VARCHAR(5),
    word_count INTEGER,
    source_chunk_id INTEGER REFERENCES raw_chunks(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Quiz results — tracks your study performance (stretch feature)
CREATE TABLE IF NOT EXISTS quiz_results (
    id SERIAL PRIMARY KEY,
    vocabulary_id INTEGER REFERENCES vocabulary(id),
    result VARCHAR(10) CHECK (result IN ('knew_it', 'didnt_know')),
    answered_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_raw_chunks_section_type ON raw_chunks(section_type);
CREATE INDEX IF NOT EXISTS idx_raw_chunks_source_file ON raw_chunks(source_file);
CREATE INDEX IF NOT EXISTS idx_vocabulary_jlpt_level ON vocabulary(jlpt_level);