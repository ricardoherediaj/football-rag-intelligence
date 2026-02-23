"""HuggingFace Spaces entrypoint — Football RAG Intelligence.

Streamlit is configured to run this file directly:
    streamlit run app.py --server.port 7860

On cold start, downloads lakehouse.duckdb from HF Dataset before rendering UI.
"""
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: sys.path + lakehouse.duckdb download (before any app imports)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LAKEHOUSE_PATH = PROJECT_ROOT / "data" / "lakehouse.duckdb"


def _download_lakehouse_if_needed() -> None:
    """Download lakehouse.duckdb from HF Dataset on cold start."""
    if LAKEHOUSE_PATH.exists():
        logger.info(f"lakehouse.duckdb present ({LAKEHOUSE_PATH.stat().st_size / 1e6:.0f} MB)")
        return

    logger.info("Cold start: downloading lakehouse.duckdb from HF Dataset...")
    LAKEHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download

        hf_hub_download(
            repo_id="rheredia8/football-rag-data",
            filename="lakehouse.duckdb",
            repo_type="dataset",
            token=os.getenv("HF_TOKEN"),
            local_dir=str(LAKEHOUSE_PATH.parent),
        )
        logger.info(f"Downloaded: {LAKEHOUSE_PATH.stat().st_size / 1e6:.0f} MB")
    except Exception as e:
        logger.error(f"Failed to download lakehouse.duckdb: {e}")
        logger.error("Vector search unavailable. Check HF_TOKEN secret and rheredia8/football-rag-data dataset.")


_download_lakehouse_if_needed()

# ---------------------------------------------------------------------------
# Streamlit UI (identical to src/football_rag/app/main.py)
# ---------------------------------------------------------------------------
import streamlit as st  # noqa: E402

from football_rag.orchestrator import query as rag_query  # noqa: E402

st.set_page_config(
    page_title="Football RAG Intelligence",
    page_icon="⚽",
    layout="centered",
)

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

user_query = st.text_input(
    label="Your query",
    placeholder="e.g. Analyze the Feyenoord vs Ajax match...",
    key="query_input",
)

provider = st.selectbox(
    "LLM provider",
    options=["anthropic", "openai", "gemini"],
    index=0,
    help="anthropic = Claude Haiku (default).",
)

submit = st.button("Analyze", type="primary", disabled=not user_query.strip())

if submit and user_query.strip():
    with st.spinner("Retrieving match data and generating analysis…"):
        result = rag_query(user_query.strip(), provider=provider)

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
            st.warning(f"Chart generated but not found at: {chart_path}")
    else:
        st.warning("Unexpected response format.")
        st.json(result)

st.divider()
st.caption("Powered by DuckDB VSS · MotherDuck · Anthropic Claude · Opik observability")
