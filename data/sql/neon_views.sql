CREATE OR REPLACE VIEW mart_study_items AS

-- Vocabulary items
SELECT
    'vocabulary'::text AS item_type,
    id,
    japanese_word AS term,
    reading,
    meaning,
    example_sentence AS example,
    jlpt_level,
    CASE
        WHEN jlpt_level = 'N2' THEN 100
        WHEN jlpt_level = 'N3' THEN 80
        ELSE 60
    END AS priority_score,
    created_at
FROM vocabulary

UNION ALL

-- Grammar items
SELECT
    'grammar'::text AS item_type,
    id,
    pattern AS term,
    NULL::varchar(100) AS reading,
    explanation AS meaning,
    example_sentence AS example,
    jlpt_level,
    CASE
        WHEN jlpt_level = 'N2' THEN 100
        WHEN jlpt_level = 'N3' THEN 80
        ELSE 60
    END AS priority_score,
    created_at
FROM grammar_rules;