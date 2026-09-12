-- Clean and standardize raw chunks for RAG
SELECT
    id,
    source_file,
    content,
    section_type,
    content_length,
    word_count,
    extracted_at,
    created_at,
    CASE
        WHEN source_file LIKE '%N2%' THEN 'N2'
        WHEN source_file LIKE '%N3%' THEN 'N3'
        ELSE 'Unknown'
    END as inferred_level
FROM raw_chunks
WHERE content IS NOT NULL
  AND LENGTH(content) > 10