"""Football RAG Intelligence — The Underdoc.

Three-panel drill-down: Team Grid → Match List → Match Report.
Dark editorial theme. Cerebras default provider (1MM free tokens/day).

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

from football_rag.app.styles import inject_css
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
    page_icon="●",
    layout="wide",
)

inject_css()


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
        st.markdown(
            '<div class="sidebar-wordmark">Football RAG<span> Intelligence</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="red-rule">', unsafe_allow_html=True)

        st.markdown(
            '<div class="section-label">Intelligence</div>',
            unsafe_allow_html=True,
        )
        provider = st.selectbox(
            "Provider",
            options=PROVIDERS,
            index=0,
            label_visibility="collapsed",
        )

        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="Your provider key (optional)",
            label_visibility="collapsed",
            help="Bring your own key. Without one, Cerebras free tier is used.",
        )

        if provider == "cerebras" and not api_key:
            st.caption("Cerebras · free · 1MM tokens/day")
        elif api_key:
            st.caption(f"Using your {provider} key.")
        elif provider == "gemini":
            st.caption(f"{provider} · add key above")
        else:
            st.caption(f"{provider} · add key above")

        st.divider()
        st.caption(
            "Keys are session-only and sent directly to the provider. Never stored."
        )

    return provider, api_key or None


# ---------------------------------------------------------------------------
# Panel 1 — Team Grid
# ---------------------------------------------------------------------------
def render_team_grid(teams: pd.DataFrame) -> None:
    st.markdown(
        '<div class="section-label">Eredivisie 2025–26 · Select a team</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="red-rule">', unsafe_allow_html=True)

    cols = st.columns(3)
    for i, row in teams.iterrows():
        col = cols[i % 3]
        with col:
            if st.button(
                row["team"],
                key=f"team_{row['team']}",
                use_container_width=True,
            ):
                st.session_state["selected_team"] = row["team"]
                st.session_state["selected_match"] = None
                st.session_state["report_result"] = None
                st.rerun()

            ppda_label = (
                f"PPDA {row['avg_ppda']}" if pd.notna(row["avg_ppda"]) else "PPDA —"
            )
            tilt_label = (
                f"Field tilt {row['avg_field_tilt']}%"
                if pd.notna(row["avg_field_tilt"])
                else ""
            )
            st.markdown(
                f'<div class="team-card-meta">'
                f"{row['matches']} matches · <strong>{ppda_label}</strong>"
                f"{' · ' + tilt_label if tilt_label else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Panel 2 — Match List
# ---------------------------------------------------------------------------
def render_match_list(team: str) -> None:
    # Back link
    if st.button("← All teams", key="back_to_teams"):
        st.session_state["selected_team"] = None
        st.session_state["selected_match"] = None
        st.session_state["report_result"] = None
        st.rerun()

    st.markdown(
        f'<div class="section-label">{team.upper()}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="red-rule">', unsafe_allow_html=True)

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
            st.markdown(
                f'<div class="match-date">{date_str}</div>',
                unsafe_allow_html=True,
            )

        with col_score:
            st.markdown(
                f'<div class="match-scoreline">'
                f'{home} <span class="score">{hg} – {ag}</span> {away}'
                f"</div>",
                unsafe_allow_html=True,
            )

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

        st.markdown(
            '<div style="border-bottom:1px solid #1e1e1e;margin:0.1rem 0;"></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Panel 3 — Match Report
# ---------------------------------------------------------------------------
def render_match_report(
    match: dict[str, Any], provider: str, api_key: str | None
) -> None:
    # Back link
    if st.button("← Match list", key="back_to_matches"):
        st.session_state["selected_match"] = None
        st.session_state["report_result"] = None
        st.rerun()

    home, away = match["home"], match["away"]

    st.markdown(
        f'<div class="report-header">{home} vs {away}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="report-subhead">{match["date"]} · {match["score"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="red-rule">', unsafe_allow_html=True)

    # Action buttons
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

    # Render result
    result = st.session_state.get("report_result")
    active_tab = st.session_state.get("active_report_tab")

    if result is None:
        st.markdown(
            '<div style="color:#555;font-size:0.85rem;margin-top:1.5rem;">'
            "Select a report type above to generate analysis."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if "error" in result:
        st.error(result["error"])
        return

    if active_tab:
        st.markdown(
            f'<div class="section-label" style="margin-top:1rem;">{active_tab.upper()}</div>',
            unsafe_allow_html=True,
        )

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

    # ── Header ──
    col_title, col_meta = st.columns([3, 1])
    with col_title:
        st.markdown(
            '<div class="underdoc-wordmark">Football RAG<span> Intelligence</span></div>',
            unsafe_allow_html=True,
        )
    with col_meta:
        st.markdown(
            '<div style="text-align:right;color:#555;font-size:0.7rem;padding-top:0.3rem;">'
            "EREDIVISIE · 2025–26"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="red-rule">', unsafe_allow_html=True)

    # ── Routing ──
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

    # ── Footer ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#333;font-size:0.65rem;letter-spacing:0.08em;">'
        "POWERED BY DUCKDB VSS · MOTHERDUCK · CEREBRAS · OPIK"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
