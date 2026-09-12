-- Unified view of all study items for the UI
SELECT
    'vocabulary' as item_type,
    id,
    japanese_word as term,
    reading,
    meaning,
    example_sentence as example,
    jlpt_level,
    priority_score,
    created_at
FROM {{ ref('stg_vocabulary') }}

UNION ALL

SELECT
    'grammar' as item_type,
    id,
    pattern as term,
    NULL as reading,
    explanation as meaning,
    example_sentence as example,
    jlpt_level,
    priority_score,
    created_at
FROM {{ ref('stg_grammar') }}