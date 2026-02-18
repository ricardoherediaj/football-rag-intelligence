{{ config(
    materialized='table',
    tags=['silver', 'events'],
    description='Cleaned, flattened WhoScored tactical events with all metrics for dashboard visualizations'
) }}

WITH raw_events AS (
    SELECT
        match_id,
        unnest(
            from_json(json_extract(data, '$.events'), '["json"]')
        ) AS event
    FROM {{ source('football_rag', 'bronze_matches') }}
    WHERE source = 'whoscored'
)
SELECT
    match_id,
    -- Event identifiers
    CAST(json_extract_string(event, '$.id') AS BIGINT) AS event_row_id,
    CAST(json_extract_string(event, '$.event_id') AS INTEGER) AS event_id,

    -- Event type and outcome (required for filtering)
    json_extract_string(event, '$.type_display_name') AS type_display_name,
    json_extract_string(event, '$.outcome_type_display_name') AS outcome_type_display_name,
    json_extract_string(event, '$.period_display_name') AS period_display_name,

    -- Qualifiers (stored as JSON for flexible filtering)
    json_extract(event, '$.qualifiers') AS qualifiers,

    -- Position data (WhoScored 0-100 pitch)
    CAST(json_extract_string(event, '$.x') AS DOUBLE) AS x,
    CAST(json_extract_string(event, '$.y') AS DOUBLE) AS y,
    CAST(json_extract_string(event, '$.end_x') AS DOUBLE) AS end_x,
    CAST(json_extract_string(event, '$.end_y') AS DOUBLE) AS end_y,

    -- StatsBomb scaled coordinates (0-120 x 0-80 for defensive heatmaps)
    CAST(json_extract_string(event, '$.x') AS DOUBLE) * 1.2 AS x_sb,
    CAST(json_extract_string(event, '$.y') AS DOUBLE) * 0.8 AS y_sb,

    -- Players and teams
    CAST(json_extract_string(event, '$.player_id') AS INTEGER) AS player_id,
    CAST(json_extract_string(event, '$.team_id') AS INTEGER) AS team_id,

    -- Timing
    CAST(json_extract_string(event, '$.minute') AS INTEGER) AS minute,
    CAST(json_extract_string(event, '$.second') AS DOUBLE) AS second,

    -- Event outcome flags
    json_extract_string(event, '$.is_shot') = 'true' AS is_shot,
    json_extract_string(event, '$.is_goal') = 'true' AS is_goal,
    json_extract_string(event, '$.is_touch') = 'true' AS is_touch,

    -- Progressive pass distance (FIFA 105x68 pitch to goal-weighted distance)
    -- Used for identifying progressive passes (threshold >= 9.11 meters)
    CASE
        WHEN json_extract_string(event, '$.type_display_name') = 'Pass' THEN
            SQRT(POWER(105 - CAST(json_extract_string(event, '$.x') AS DOUBLE), 2) +
                 POWER(34 - CAST(json_extract_string(event, '$.y') AS DOUBLE), 2)) -
            SQRT(POWER(105 - CAST(json_extract_string(event, '$.end_x') AS DOUBLE), 2) +
                 POWER(34 - CAST(json_extract_string(event, '$.end_y') AS DOUBLE), 2))
        ELSE 0.0
    END AS prog_pass
FROM raw_events
