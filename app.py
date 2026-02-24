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

# MotherDuck reads `motherduck_token` (lowercase); HF Spaces secret is MOTHERDUCK_TOKEN
if os.getenv("MOTHERDUCK_TOKEN") and not os.getenv("motherduck_token"):
    os.environ["motherduck_token"] = os.environ["MOTHERDUCK_TOKEN"]


_DOWNLOAD_ERROR: str = ""

FREE_QUERY_LIMIT = 5


def _download_lakehouse_if_needed() -> None:
    """Download lakehouse.duckdb from HF Dataset on cold start."""
    global _DOWNLOAD_ERROR

    if LAKEHOUSE_PATH.exists() and LAKEHOUSE_PATH.stat().st_size > 1_000_000:
        logger.info(f"lakehouse.duckdb present ({LAKEHOUSE_PATH.stat().st_size / 1e6:.0f} MB)")
        return

    logger.info("Cold start: downloading lakehouse.duckdb from HF Dataset...")
    LAKEHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download

        token = os.getenv("HF_TOKEN")
        if not token:
            raise ValueError("HF_TOKEN secret not set — cannot download private dataset")

        dest = hf_hub_download(
            repo_id="rheredia8/football-rag-data",
            filename="lakehouse.duckdb",
            repo_type="dataset",
            token=token,
            local_dir=str(LAKEHOUSE_PATH.parent),
        )
        size_mb = Path(dest).stat().st_size / 1e6
        logger.info(f"Downloaded: {dest} ({size_mb:.0f} MB)")
        if size_mb < 100:
            raise ValueError(f"Downloaded file too small ({size_mb:.0f} MB) — likely corrupt")
    except Exception as e:
        _DOWNLOAD_ERROR = str(e)
        logger.error(f"Failed to download lakehouse.duckdb: {e}")


_download_lakehouse_if_needed()

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
import streamlit as st  # noqa: E402

from football_rag.orchestrator import query as rag_query  # noqa: E402

st.set_page_config(
    page_title="Football RAG Intelligence",
    page_icon="⚽",
    layout="wide",
)

if _DOWNLOAD_ERROR:
    st.error(f"Failed to load vector database: {_DOWNLOAD_ERROR}")
    st.stop()

if "query_count" not in st.session_state:
    st.session_state["query_count"] = 0

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Football RAG Intelligence")
st.markdown(
    "Eredivisie 2025-26 · **205 matches** · Grounded by real event data  \n"
    "Ask about tactics, passing networks, shot maps, or team comparisons."
)

# ---------------------------------------------------------------------------
# Query input row
# ---------------------------------------------------------------------------
col_query, col_provider, col_btn = st.columns([6, 1.5, 1])

with col_query:
    user_query = st.text_input(
        label="Your query",
        placeholder="e.g. Why did Heracles beat NEC despite lower possession?",
        key="query_input",
        label_visibility="collapsed",
    )

with col_provider:
    provider = st.selectbox(
        "Provider",
        options=["anthropic", "openai", "gemini"],
        index=0,
        label_visibility="collapsed",
    )

with col_btn:
    submit = st.button("Analyze", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# API key + demo status (compact expander)
# ---------------------------------------------------------------------------
with st.expander("Bring your own API key (optional)"):
    key_col, status_col = st.columns([2, 1])
    with key_col:
        user_api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="sk-... (Anthropic, OpenAI, or Gemini key)",
            label_visibility="collapsed",
        )
        st.caption("Never stored. Used only for this session, sent directly to the provider.")
    with status_col:
        if user_api_key:
            st.success("Your key active — unlimited queries.")
        else:
            used = st.session_state.get("query_count", 0)
            remaining = max(0, FREE_QUERY_LIMIT - used)
            st.info(f"Demo mode: **{remaining}/{FREE_QUERY_LIMIT}** free queries left.")

# ---------------------------------------------------------------------------
# Example queries (clickable)
# ---------------------------------------------------------------------------
st.markdown(
    "<small><b>Try:</b> "
    "<em>Show the shot map from Fortuna Sittard vs Go Ahead Eagles</em> · "
    "<em>Analyze Ajax vs Feyenoord</em> · "
    "<em>Show me the passing network for PSV vs AZ</em></small>",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Query execution with rate limiting
# ---------------------------------------------------------------------------
if submit and user_query.strip():
    if not user_api_key and st.session_state["query_count"] >= FREE_QUERY_LIMIT:
        st.warning(
            f"You've used all {FREE_QUERY_LIMIT} free queries. "
            "Add your own API key above for unlimited access."
        )
    else:
        api_key = user_api_key if user_api_key else None

        with st.spinner("Retrieving match data and generating analysis..."):
            result = rag_query(user_query.strip(), provider=provider, api_key=api_key)

        if not user_api_key:
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
                st.image(str(chart_path), use_column_width=True)
            else:
                st.warning(f"Chart generated but not found at: {chart_path}")
        else:
            st.warning("Unexpected response format.")
            st.json(result)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.caption("Powered by DuckDB VSS · MotherDuck · Anthropic Claude · Opik observability")
