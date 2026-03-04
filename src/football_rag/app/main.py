"""Football RAG Intelligence.

Three-panel drill-down: Team Grid → Match List → Match Report.
Dark editorial theme via .streamlit/config.toml.
Cerebras default provider (1MM free tokens/day).

Run locally:
    uv run streamlit run src/football_rag/app/main.py
"""

import os
import logging
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import streamlit as st
from huggingface_hub import hf_hub_download

from football_rag.orchestrator import query as rag_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPORT_QUERIES: dict[str, str] = {
    "Tactical Report": "Analyze the {home} vs {away} match",
    "Passing Network": "Show the passing network for {home} vs {away}",
    "Shot Map": "Show the shot map for {home} vs {away}",
    "Dashboard": "Show the full dashboard for {home} vs {away}",
}

PROVIDERS = ["cerebras", "anthropic", "openai", "gemini"]

# ---------------------------------------------------------------------------
# Page config (must be first st call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Football RAG Intelligence",
    page_icon="⚽",
    layout="wide",
)


# ---------------------------------------------------------------------------
# lakehouse.duckdb bootstrap — download from HF Dataset if not present
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Downloading match database (first load only)…")
def ensure_lakehouse() -> Path:
    """Download lakehouse.duckdb from HF Dataset if not already on disk."""
    db_path = Path("data/lakehouse.duckdb")
    if db_path.exists():
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    hf_token = os.environ.get("HF_TOKEN")
    downloaded = hf_hub_download(
        repo_id="rheredia8/football-rag-data",
        filename="lakehouse.duckdb",
        repo_type="dataset",
        token=hf_token,
        local_dir=str(db_path.parent),
    )
    return Path(downloaded)


# ---------------------------------------------------------------------------
# Data layer — MotherDuck queries (cached per session)
# ---------------------------------------------------------------------------
def _get_md_conn() -> duckdb.DuckDBPyConnection:
    """Return a MotherDuck connection, cached in session state."""
    if "md_conn" not in st.session_state:
        token = os.environ.get("motherduck_token") or os.environ.get(
            "MOTHERDUCK_TOKEN", ""
        )
        conn = duckdb.connect(f"md:?motherduck_token={token}" if token else "md:")
        st.session_state["md_conn"] = conn
    return st.session_state["md_conn"]


@st.cache_data(ttl=3600, show_spinner=False)
def load_team_stats() -> pd.DataFrame:
    """Aggregate team stats from gold_match_summaries for the team grid."""
    conn = _get_md_conn()
    return conn.execute(
        """
        SELECT
            team,
            COUNT(*) AS matches,
            ROUND(AVG(ppda), 1) AS avg_ppda,
            ROUND(AVG(field_tilt), 1) AS avg_field_tilt
        FROM (
            SELECT home_team AS team, home_ppda AS ppda, home_field_tilt AS field_tilt
            FROM football_rag.main_main.gold_match_summaries
            UNION ALL
            SELECT away_team, away_ppda, away_field_tilt
            FROM football_rag.main_main.gold_match_summaries
        )
        GROUP BY team
        ORDER BY team
        """
    ).df()


@st.cache_data(ttl=3600, show_spinner=False)
def load_matches_for_team(team: str) -> pd.DataFrame:
    """Load all matches involving a team, most recent first."""
    conn = _get_md_conn()
    return conn.execute(
        """
        SELECT match_id, home_team, away_team, match_date, home_goals, away_goals
        FROM football_rag.main_main.gold_match_summaries
        WHERE home_team = ? OR away_team = ?
        ORDER BY match_date DESC
        """,
        [team, team],
    ).df()


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
def _init_state() -> None:
    for key, default in [
        ("selected_team", None),
        ("selected_match", None),
        ("report_result", None),
        ("active_report_tab", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar() -> tuple[str, str | None]:
    """Render sidebar, return (provider, api_key)."""
    with st.sidebar:
        st.title("Football RAG Intelligence")
        st.caption("Eredivisie 2025–26 · Tactical scouting powered by AI")
        st.divider()

        provider = st.selectbox(
            "LLM Provider",
            options=PROVIDERS,
            index=0,
        )

        api_key = st.text_input(
            "API Key (optional)",
            type="password",
            placeholder="Your provider key",
            help="Bring your own key. Without one, Cerebras free tier is used.",
        )

        if provider == "cerebras" and not api_key:
            st.caption("✓ Cerebras · free · ~1MM tokens/day")
        elif api_key:
            st.caption(f"✓ Using your {provider} key")
        else:
            st.caption(f"{provider} · add key above")

        st.divider()
        st.caption("Keys are session-only. Never stored.")

    return provider, api_key or None


# ---------------------------------------------------------------------------
# Panel 1 — Team Grid
# ---------------------------------------------------------------------------
def render_team_grid(teams: pd.DataFrame) -> None:
    st.caption("EREDIVISIE 2025–26 · SELECT A TEAM")
    st.divider()

    cols = st.columns(3)
    for i, row in teams.iterrows():
        col = cols[i % 3]
        with col:
            ppda = f"{row['avg_ppda']}" if pd.notna(row["avg_ppda"]) else "—"
            tilt = (
                f"{row['avg_field_tilt']}%" if pd.notna(row["avg_field_tilt"]) else "—"
            )
            label = (
                f"{row['team']}\n{row['matches']} matches · PPDA {ppda} · Tilt {tilt}"
            )
            if st.button(
                label,
                key=f"team_{row['team']}",
                use_container_width=True,
            ):
                st.session_state["selected_team"] = row["team"]
                st.session_state["selected_match"] = None
                st.session_state["report_result"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Panel 2 — Match List
# ---------------------------------------------------------------------------
def render_match_list(team: str) -> None:
    if st.button("← All teams", key="back_to_teams"):
        st.session_state["selected_team"] = None
        st.session_state["selected_match"] = None
        st.session_state["report_result"] = None
        st.rerun()

    st.subheader(team)
    st.divider()

    with st.spinner("Loading matches…"):
        matches = load_matches_for_team(team)

    if matches.empty:
        st.warning("No matches found for this team.")
        return

    for _, row in matches.iterrows():
        home, away = row["home_team"], row["away_team"]
        hg, ag = int(row["home_goals"] or 0), int(row["away_goals"] or 0)
        date_str = str(row["match_date"])[:10]

        col_date, col_score, col_btn = st.columns([2, 5, 2])

        with col_date:
            st.caption(date_str)

        with col_score:
            st.write(f"**{home}** {hg} – {ag} **{away}**")

        with col_btn:
            if st.button("Open →", key=f"match_{row['match_id']}"):
                st.session_state["selected_match"] = {
                    "match_id": row["match_id"],
                    "home": home,
                    "away": away,
                    "date": date_str,
                    "score": f"{hg}–{ag}",
                }
                st.session_state["report_result"] = None
                st.session_state["active_report_tab"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Panel 3 — Match Report
# ---------------------------------------------------------------------------
def render_match_report(
    match: dict[str, Any], provider: str, api_key: str | None
) -> None:
    if st.button("← Match list", key="back_to_matches"):
        st.session_state["selected_match"] = None
        st.session_state["report_result"] = None
        st.rerun()

    home, away = match["home"], match["away"]

    st.subheader(f"{home} vs {away}")
    st.caption(f"{match['date']} · {match['score']}")
    st.divider()

    btn_cols = st.columns(len(REPORT_QUERIES))
    clicked_tab = None
    for col, tab_name in zip(btn_cols, REPORT_QUERIES):
        with col:
            if st.button(tab_name, key=f"tab_{tab_name}", use_container_width=True):
                clicked_tab = tab_name

    if clicked_tab:
        st.session_state["active_report_tab"] = clicked_tab
        query_str = REPORT_QUERIES[clicked_tab].format(home=home, away=away)
        with st.spinner(f"Generating {clicked_tab.lower()}…"):
            result = rag_query(query_str, provider=provider, api_key=api_key)
        st.session_state["report_result"] = result

    result = st.session_state.get("report_result")
    active_tab = st.session_state.get("active_report_tab")

    if result is None:
        st.caption("Select a report type above to generate analysis.")
        return

    if "error" in result:
        st.error(result["error"])
        return

    if active_tab:
        st.caption(active_tab.upper())

    if "commentary" in result:
        st.markdown(result["commentary"])
        with st.expander("Metrics used", expanded=False):
            st.json(result.get("metrics_used", {}))

    elif "chart_path" in result:
        chart_path = Path(result["chart_path"])
        if chart_path.exists():
            st.image(str(chart_path), use_container_width=True)
        else:
            st.warning(f"Chart not found at: {chart_path}")

    else:
        st.warning("Unexpected response format.")
        st.json(result)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _init_state()
    provider, api_key = render_sidebar()
    ensure_lakehouse()  # download once, cached for the process lifetime

    st.title("Football RAG Intelligence")
    st.caption("EREDIVISIE · 2025–26")
    st.divider()

    selected_match = st.session_state.get("selected_match")
    selected_team = st.session_state.get("selected_team")

    if selected_match:
        render_match_report(selected_match, provider, api_key)
    elif selected_team:
        render_match_list(selected_team)
    else:
        with st.spinner("Loading league data…"):
            try:
                teams = load_team_stats()
            except Exception as e:
                st.error(f"Could not load team data: {e}")
                return
        render_team_grid(teams)

    st.divider()
    st.caption("POWERED BY DUCKDB VSS · MOTHERDUCK · CEREBRAS · OPIK")


if __name__ == "__main__":
    main()
