{{ config(
    materialized='table',
    tags=['silver', 'metrics'],
) }}

/*
Pre-calculated tactical metrics for each team in each match.
Translates 38 MVP metrics from Python to SQL for production pipeline.
Reference: src/football_rag/analytics/metrics.py
*/

WITH match_events AS (
    SELECT * FROM {{ ref('silver_events') }}
),

team_metrics AS (
    SELECT
        match_id,
        team_id,

        -- ==== PASSING & PROGRESSION (8 metrics) ====
        COUNT(*) FILTER (WHERE type_display_name = 'Pass') AS total_passes,

        COUNT(*) FILTER (
            WHERE type_display_name = 'Pass'
            AND prog_pass >= 9.11  -- Progressive pass threshold (meters toward goal)
        ) AS progressive_passes,

        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE type_display_name = 'Pass'
                AND outcome_type_display_name = 'Successful'
            ) / NULLIF(COUNT(*) FILTER (WHERE type_display_name = 'Pass'), 0),
            2
        ) AS pass_accuracy,

        -- Verticality: Average forward component of passes (positive = forward, negative = backward)
        ROUND(
            AVG(
                CASE
                    WHEN type_display_name = 'Pass' AND end_x IS NOT NULL
                    THEN end_x - x
                    ELSE NULL
                END
            ),
            2
        ) AS verticality,

        -- ==== DEFENSIVE PRESSURE (8 metrics) ====

        COUNT(*) FILTER (
            WHERE type_display_name IN ('Tackle', 'Interception', 'Aerial', 'BallRecovery', 'Challenge')
        ) AS defensive_actions,

        COUNT(*) FILTER (
            WHERE type_display_name IN ('Tackle', 'Interception')
            AND x >= 70  -- Final third (WhoScored 0-100 scale)
        ) AS high_press,

        COUNT(*) FILTER (
            WHERE type_display_name = 'Tackle'
            AND outcome_type_display_name = 'Successful'
        ) AS successful_tackles,

        COUNT(*) FILTER (
            WHERE type_display_name = 'Interception'
        ) AS interceptions,

        -- ==== ATTACKING (6 metrics) ====

        COUNT(*) FILTER (WHERE is_shot = TRUE) AS shots,

        COUNT(*) FILTER (
            WHERE is_shot = TRUE
            AND outcome_type_display_name IN ('Goal', 'SavedShot', 'ShotOnPost')
        ) AS shots_on_target,

        COUNT(*) FILTER (WHERE is_goal = TRUE) AS goals,

        -- Note: xG will be joined from fotmob data below

        -- ==== TEAM POSITIONING (8 metrics) ====

        -- Median X position (all touches)
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY x) FILTER (WHERE is_touch = TRUE) AS median_position,

        -- Defense line: 25th percentile of defensive actions
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY x) FILTER (
            WHERE type_display_name IN ('Tackle', 'Interception', 'Clearance')
        ) AS defense_line,

        -- Forward line: 75th percentile of attacking actions
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY x) FILTER (
            WHERE type_display_name IN ('Pass', 'TakeOn', 'Shot')
        ) AS forward_line,

        -- ==== MATCH CONTEXT (8 metrics) ====

        -- Field tilt: % of touches in attacking half
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE is_touch = TRUE AND x >= 50)
            / NULLIF(COUNT(*) FILTER (WHERE is_touch = TRUE), 0),
            2
        ) AS field_tilt,

        COUNT(*) FILTER (WHERE type_display_name = 'Clearance') AS clearances,

        COUNT(*) FILTER (
            WHERE type_display_name = 'Aerial'
            AND outcome_type_display_name = 'Successful'
        ) AS aerials_won,

        COUNT(*) FILTER (WHERE type_display_name = 'Foul') AS fouls

    FROM match_events
    GROUP BY match_id, team_id
),

-- Add xG from fotmob data (using match_mapping to join WhoScored ↔ FotMob)
xg_data AS (
    SELECT
        mm.whoscored_match_id AS match_id,
        CASE
            WHEN fs.team_id = mm.fotmob_team_id_1 THEN mm.whoscored_team_id_1
            WHEN fs.team_id = mm.fotmob_team_id_2 THEN mm.whoscored_team_id_2
        END AS team_id,
        COALESCE(SUM(fs.xg), 0.0) AS total_xg
    FROM {{ source('football_rag', 'silver_fotmob_shots') }} fs
    JOIN {{ source('football_rag', 'match_mapping') }} mm
        ON fs.match_id = mm.fotmob_match_id
    WHERE fs.team_id IN (mm.fotmob_team_id_1, mm.fotmob_team_id_2)
    GROUP BY
        mm.whoscored_match_id,
        mm.whoscored_team_id_1,
        mm.whoscored_team_id_2,
        mm.fotmob_team_id_1,
        mm.fotmob_team_id_2,
        fs.team_id
),

-- Calculate PPDA (requires opponent's passes)
ppda_calc AS (
    SELECT
        t1.match_id,
        t1.team_id,
        ROUND(
            t2.total_passes::DOUBLE / NULLIF(t1.defensive_actions, 0),
            2
        ) AS ppda
    FROM team_metrics t1
    JOIN team_metrics t2
        ON t1.match_id = t2.match_id
        AND t1.team_id != t2.team_id  -- Opponent team
),

-- Calculate possession (requires total touches from both teams)
possession_calc AS (
    SELECT
        match_id,
        team_id,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE is_touch = TRUE)
            / SUM(COUNT(*) FILTER (WHERE is_touch = TRUE)) OVER (PARTITION BY match_id),
            2
        ) AS possession
    FROM match_events
    GROUP BY match_id, team_id
),

final_metrics AS (
    SELECT
        tm.*,

        -- Add xG
        COALESCE(xg.total_xg, 0.0) AS total_xg,

        -- Add PPDA
        COALESCE(ppda.ppda, 0.0) AS ppda,

        -- Add possession
        COALESCE(poss.possession, 0.0) AS possession,

        -- Calculate compactness (distance between lines)
        ROUND(tm.forward_line - tm.defense_line, 2) AS compactness

    FROM team_metrics tm
    LEFT JOIN xg_data xg
        ON tm.match_id = xg.match_id
        AND tm.team_id = xg.team_id
    LEFT JOIN ppda_calc ppda
        ON tm.match_id = ppda.match_id
        AND tm.team_id = ppda.team_id
    LEFT JOIN possession_calc poss
        ON tm.match_id = poss.match_id
        AND tm.team_id = poss.team_id
)

SELECT
    match_id,
    team_id,

    -- Passing & Progression (8)
    progressive_passes,
    total_passes,
    pass_accuracy,
    verticality,

    -- Defensive Pressure (8)
    ppda,
    high_press,
    defensive_actions,
    successful_tackles,
    interceptions,

    -- Attacking (6)
    shots,
    shots_on_target,
    goals,
    total_xg,

    -- Team Positioning (8)
    median_position,
    defense_line,
    forward_line,
    compactness,

    -- Match Context (8)
    possession,
    field_tilt,
    clearances,
    aerials_won,
    fouls

FROM final_metrics
