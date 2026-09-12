-- Clean and standardize vocabulary data
SELECT
    id,
    japanese_word,
    reading,
    meaning,
    example_sentence,
    jlpt_level,
    created_at,
    CASE 
        WHEN jlpt_level = 'N2' THEN 100
        WHEN jlpt_level = 'N3' THEN 80
        ELSE 60
    END as priority_score
FROM vocabulary
WHERE japanese_word IS NOT NULL
  AND LENGTH(japanese_word) > 0