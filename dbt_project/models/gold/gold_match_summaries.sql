{{ config(
    materialized='table',
    tags=['gold', 'embeddings'],
) }}

/*
Match-level aggregations combining Silver metrics for LLM consumption.
Uses match_mapping as source of truth for home/away team identification.
Provides all metadata needed for downstream visualizations (team names, IDs, FotMob match_id).
Creates tactical narrative summary for embedding generation.
*/

WITH match_metadata AS (
    SELECT
        mm.whoscored_match_id AS match_id,
        mm.fotmob_match_id,
        mm.home_team,
        mm.away_team,
        mm.match_date,
        CAST(json_extract_string(bm.data, '$.league') AS VARCHAR) AS league,
        CAST(json_extract_string(bm.data, '$.season') AS VARCHAR) AS season,
        -- WhoScored team IDs (for joining to silver_team_metrics)
        mm.whoscored_team_id_1 AS home_whoscored_id,
        mm.whoscored_team_id_2 AS away_whoscored_id,
        -- FotMob team IDs (for visualizers to filter shot data)
        CAST(mm.fotmob_team_id_1 AS INTEGER) AS home_fotmob_id,
        CAST(mm.fotmob_team_id_2 AS INTEGER) AS away_fotmob_id
    FROM {{ source('football_rag', 'match_mapping') }} mm
    JOIN {{ source('football_rag', 'bronze_matches') }} bm
        ON mm.whoscored_match_id = bm.match_id
        AND bm.source = 'whoscored'
),

-- Get home team metrics (using explicit team ID from match_mapping)
home_metrics AS (
    SELECT
        stm.match_id,
        stm.progressive_passes AS home_progressive_passes,
        stm.total_passes AS home_total_passes,
        stm.pass_accuracy AS home_pass_accuracy,
        stm.verticality AS home_verticality,
        stm.ppda AS home_ppda,
        stm.high_press AS home_high_press,
        stm.defensive_actions AS home_defensive_actions,
        stm.successful_tackles AS home_successful_tackles,
        stm.interceptions AS home_interceptions,
        stm.shots AS home_shots,
        stm.shots_on_target AS home_shots_on_target,
        stm.goals AS home_goals,
        stm.total_xg AS home_total_xg,
        stm.median_position AS home_median_position,
        stm.defense_line AS home_defense_line,
        stm.forward_line AS home_forward_line,
        stm.compactness AS home_compactness,
        stm.possession AS home_possession,
        stm.field_tilt AS home_field_tilt,
        stm.clearances AS home_clearances,
        stm.aerials_won AS home_aerials_won,
        stm.fouls AS home_fouls
    FROM {{ ref('silver_team_metrics') }} stm
    JOIN match_metadata mm
        ON stm.match_id = mm.match_id
        AND stm.team_id = mm.home_whoscored_id
),

-- Get away team metrics (using explicit team ID from match_mapping)
away_metrics AS (
    SELECT
        stm.match_id,
        stm.progressive_passes AS away_progressive_passes,
        stm.total_passes AS away_total_passes,
        stm.pass_accuracy AS away_pass_accuracy,
        stm.verticality AS away_verticality,
        stm.ppda AS away_ppda,
        stm.high_press AS away_high_press,
        stm.defensive_actions AS away_defensive_actions,
        stm.successful_tackles AS away_successful_tackles,
        stm.interceptions AS away_interceptions,
        stm.shots AS away_shots,
        stm.shots_on_target AS away_shots_on_target,
        stm.goals AS away_goals,
        stm.total_xg AS away_total_xg,
        stm.median_position AS away_median_position,
        stm.defense_line AS away_defense_line,
        stm.forward_line AS away_forward_line,
        stm.compactness AS away_compactness,
        stm.possession AS away_possession,
        stm.field_tilt AS away_field_tilt,
        stm.clearances AS away_clearances,
        stm.aerials_won AS away_aerials_won,
        stm.fouls AS away_fouls
    FROM {{ ref('silver_team_metrics') }} stm
    JOIN match_metadata mm
        ON stm.match_id = mm.match_id
        AND stm.team_id = mm.away_whoscored_id
),

combined AS (
    SELECT
        mm.match_id,
        mm.fotmob_match_id,
        mm.home_team,
        mm.away_team,
        mm.match_date,
        mm.league,
        mm.season,
        mm.home_whoscored_id,
        mm.away_whoscored_id,
        mm.home_fotmob_id,
        mm.away_fotmob_id,

        -- Home metrics (24)
        hm.home_progressive_passes,
        hm.home_total_passes,
        hm.home_pass_accuracy,
        hm.home_verticality,
        hm.home_ppda,
        hm.home_high_press,
        hm.home_defensive_actions,
        hm.home_successful_tackles,
        hm.home_interceptions,
        hm.home_shots,
        hm.home_shots_on_target,
        hm.home_goals,
        hm.home_total_xg,
        hm.home_median_position,
        hm.home_defense_line,
        hm.home_forward_line,
        hm.home_compactness,
        hm.home_possession,
        hm.home_field_tilt,
        hm.home_clearances,
        hm.home_aerials_won,
        hm.home_fouls,

        -- Away metrics (24)
        am.away_progressive_passes,
        am.away_total_passes,
        am.away_pass_accuracy,
        am.away_verticality,
        am.away_ppda,
        am.away_high_press,
        am.away_defensive_actions,
        am.away_successful_tackles,
        am.away_interceptions,
        am.away_shots,
        am.away_shots_on_target,
        am.away_goals,
        am.away_total_xg,
        am.away_median_position,
        am.away_defense_line,
        am.away_forward_line,
        am.away_compactness,
        am.away_possession,
        am.away_field_tilt,
        am.away_clearances,
        am.away_aerials_won,
        am.away_fouls

    FROM match_metadata mm
    LEFT JOIN home_metrics hm ON mm.match_id = hm.match_id
    LEFT JOIN away_metrics am ON mm.match_id = am.match_id
)

SELECT
    -- Identifiers (for joining to Bronze for shot data, events, etc.)
    match_id,
    fotmob_match_id,

    -- Team metadata (for visualizer labels and filtering)
    home_team,
    away_team,
    match_date,
    league,
    season,

    -- Team IDs (for downstream joins)
    home_whoscored_id,
    away_whoscored_id,
    home_fotmob_id,
    away_fotmob_id,

    -- Home metrics (24)
    home_progressive_passes,
    home_total_passes,
    home_pass_accuracy,
    home_verticality,
    home_ppda,
    home_high_press,
    home_defensive_actions,
    home_successful_tackles,
    home_interceptions,
    home_shots,
    home_shots_on_target,
    home_goals,
    home_total_xg,
    home_median_position,
    home_defense_line,
    home_forward_line,
    home_compactness,
    home_possession,
    home_field_tilt,
    home_clearances,
    home_aerials_won,
    home_fouls,

    -- Away metrics (24)
    away_progressive_passes,
    away_total_passes,
    away_pass_accuracy,
    away_verticality,
    away_ppda,
    away_high_press,
    away_defensive_actions,
    away_successful_tackles,
    away_interceptions,
    away_shots,
    away_shots_on_target,
    away_goals,
    away_total_xg,
    away_median_position,
    away_defense_line,
    away_forward_line,
    away_compactness,
    away_possession,
    away_field_tilt,
    away_clearances,
    away_aerials_won,
    away_fouls,

    -- Summary text for embedding (tactical narrative with team names)
    home_team || ' vs ' || away_team ||
    ' | ' || league || ' (' || season || ')' ||
    ' | Score: ' || CAST(COALESCE(home_goals, 0) AS VARCHAR) || '-' || CAST(COALESCE(away_goals, 0) AS VARCHAR) ||
    ' | Home PPDA: ' || CAST(ROUND(COALESCE(home_ppda, 0), 1) AS VARCHAR) ||
    ' | Away PPDA: ' || CAST(ROUND(COALESCE(away_ppda, 0), 1) AS VARCHAR) ||
    ' | Home Field Tilt: ' || CAST(ROUND(COALESCE(home_field_tilt, 0), 1) AS VARCHAR) || '%' ||
    ' | Away Field Tilt: ' || CAST(ROUND(COALESCE(away_field_tilt, 0), 1) AS VARCHAR) || '%' ||
    ' | Home xG: ' || CAST(ROUND(COALESCE(home_total_xg, 0), 2) AS VARCHAR) ||
    ' | Away xG: ' || CAST(ROUND(COALESCE(away_total_xg, 0), 2) AS VARCHAR) ||
    ' | Home Progressive Passes: ' || CAST(COALESCE(home_progressive_passes, 0) AS VARCHAR) ||
    ' | Away Progressive Passes: ' || CAST(COALESCE(away_progressive_passes, 0) AS VARCHAR) ||
    ' | Home Possession: ' || CAST(ROUND(COALESCE(home_possession, 0), 1) AS VARCHAR) || '%' ||
    ' | Away Possession: ' || CAST(ROUND(COALESCE(away_possession, 0), 1) AS VARCHAR) || '%' ||
    ' | Home Shots: ' || CAST(COALESCE(home_shots, 0) AS VARCHAR) ||
    ' | Away Shots: ' || CAST(COALESCE(away_shots, 0) AS VARCHAR) ||
    ' | Home Shots on Target: ' || CAST(COALESCE(home_shots_on_target, 0) AS VARCHAR) ||
    ' | Away Shots on Target: ' || CAST(COALESCE(away_shots_on_target, 0) AS VARCHAR) ||
    ' | Home Pass Accuracy: ' || CAST(ROUND(COALESCE(home_pass_accuracy, 0), 1) AS VARCHAR) || '%' ||
    ' | Away Pass Accuracy: ' || CAST(ROUND(COALESCE(away_pass_accuracy, 0), 1) AS VARCHAR) || '%'
    AS summary_text

FROM combined
