-- Clean and standardize grammar data
SELECT
    id,
    pattern,
    explanation,
    example_sentence,
    jlpt_level,
    created_at,
    CASE 
        WHEN jlpt_level = 'N2' THEN 100
        WHEN jlpt_level = 'N3' THEN 80
        ELSE 60
    END as priority_score
FROM grammar_rules
WHERE pattern IS NOT NULL
  AND LENGTH(pattern) > 0