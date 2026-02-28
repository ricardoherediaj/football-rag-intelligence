"""Football RAG Intelligence — Streamlit UI.

Single-page app: query textbox → orchestrator.query() → commentary + optional chart.

Run locally:
    uv run streamlit run src/football_rag/app/main.py
"""

import streamlit as st
from pathlib import Path

from football_rag.orchestrator import query as rag_query

FREE_QUERY_LIMIT = 5

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Football RAG Intelligence",
    page_icon="⚽",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Sidebar: API key + provider config
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    user_api_key = st.text_input(
        "API Key (optional)",
        type="password",
        placeholder="sk-... or your provider key",
        help="Bring your own key for unlimited queries. Without one, you get "
        f"{FREE_QUERY_LIMIT} free queries per session.",
    )

    provider = st.selectbox(
        "LLM provider",
        options=["anthropic", "openai", "gemini", "ollama"],
        index=0,
        help="anthropic = Claude Haiku (default). Requires API key in env.",
    )

    st.divider()

    if user_api_key:
        st.success("Using your API key — unlimited queries.")
    elif provider == "ollama":
        st.info("Ollama: running locally, no API key needed.")
    else:
        used = st.session_state.get("query_count", 0)
        remaining = max(0, FREE_QUERY_LIMIT - used)
        st.info(f"Demo mode: {remaining}/{FREE_QUERY_LIMIT} free queries left.")

    st.caption(
        "Keys are never stored. They are used only for the current session "
        "and sent directly to the LLM provider."
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("⚽ Football RAG Intelligence")
st.caption("Eredivisie 2025-26 · 205 matches · Grounded by real event data")

st.markdown(
    """
Ask anything about Eredivisie matches — tactical analysis, passing networks,
shot maps, or team comparisons.

**Example queries:**
- *Why did Heracles beat NEC Nijmegen despite lower possession?*
- *Show me the passing network for Ajax vs Feyenoord*
- *Analyze PSV Eindhoven's pressing intensity last match*
- *Show the shot map from Fortuna Sittard vs Go Ahead Eagles*
"""
)

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
user_query = st.text_input(
    label="Your query",
    placeholder="e.g. Analyze the Feyenoord vs Ajax match...",
    key="query_input",
)

submit = st.button("Analyze", type="primary", disabled=not user_query.strip())

# ---------------------------------------------------------------------------
# Query execution with rate limiting
# ---------------------------------------------------------------------------
if "query_count" not in st.session_state:
    st.session_state["query_count"] = 0

if submit and user_query.strip():
    uses_own_key = bool(user_api_key) or provider == "ollama"

    if not uses_own_key and st.session_state["query_count"] >= FREE_QUERY_LIMIT:
        st.warning(
            f"You've used all {FREE_QUERY_LIMIT} free queries for this session. "
            "Enter your own API key in the sidebar for unlimited access."
        )
    else:
        api_key = user_api_key if user_api_key else None

        with st.spinner("Retrieving match data and generating analysis…"):
            result = rag_query(user_query.strip(), provider=provider, api_key=api_key)

        if not uses_own_key:
            st.session_state["query_count"] += 1

        if "error" in result:
            st.error(result["error"])

        elif "commentary" in result:
            st.success(f"**{result['match_name']}**")
            st.markdown(result["commentary"])

            with st.expander("Metrics used"):
                st.json(result.get("metrics_used", {}))

        elif "chart_path" in result:
            st.success(f"**{result['match_name']}**")
            chart_path = Path(result["chart_path"])
            if chart_path.exists():
                st.image(str(chart_path), use_container_width=True)
            else:
                st.warning(f"Chart was generated but not found at: {chart_path}")

        else:
            st.warning("Unexpected response format.")
            st.json(result)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("Powered by DuckDB VSS · MotherDuck · Anthropic Claude · Opik observability")
