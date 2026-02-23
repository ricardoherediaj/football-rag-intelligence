"""Football RAG Intelligence — Streamlit UI.

Single-page app: query textbox → orchestrator.query() → commentary + optional chart.

Run locally:
    uv run streamlit run src/football_rag/app/main.py
"""

import os
import streamlit as st
from pathlib import Path

from football_rag.orchestrator import query as rag_query

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Football RAG Intelligence",
    page_icon="⚽",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("⚽ Football RAG Intelligence")
st.caption(
    "Eredivisie 2025-26 · 205 matches · Grounded by real event data"
)

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

provider = st.selectbox(
    "LLM provider",
    options=["anthropic", "openai", "gemini", "ollama"],
    index=0,
    help="anthropic = Claude Haiku (default). Requires API key in env.",
)

submit = st.button("Analyze", type="primary", disabled=not user_query.strip())

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if submit and user_query.strip():
    with st.spinner("Retrieving match data and generating analysis…"):
        result = rag_query(user_query.strip(), provider=provider)

    if "error" in result:
        st.error(result["error"])

    elif "commentary" in result:
        # Text / semantic path
        st.success(f"**{result['match_name']}**")
        st.markdown(result["commentary"])

        with st.expander("Metrics used"):
            st.json(result.get("metrics_used", {}))

    elif "chart_path" in result:
        # Viz path
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
st.caption(
    "Powered by DuckDB VSS · MotherDuck · Anthropic Claude · Opik observability"
)
