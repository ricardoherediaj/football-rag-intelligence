"""FastAPI backend with Gradio interface for Football RAG Intelligence."""

from typing import Tuple

import gradio as gr
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from football_rag.core.logging import get_logger, setup_logging
from football_rag.core.metrics import metrics
from football_rag.core.middleware import ObservabilityMiddleware
from football_rag.core.prompts_loader import load_prompt

setup_logging()
logger = get_logger(__name__)

# Global pipeline instance
pipeline = None
current_provider = "ollama"
current_api_key = ""


def initialize_pipeline(provider: str, api_key: str = ""):
    """Initialize RAG pipeline with selected provider."""
    global pipeline, current_provider, current_api_key
    try:
        from football_rag.models.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline(provider=provider, api_key=api_key or None)
        current_provider = provider
        current_api_key = api_key
        logger.info(f"✓ Pipeline initialized with {provider}")
        return True
    except Exception as e:
        logger.error(f"Pipeline init failed: {e}")
        return False


def format_faithfulness_indicator(score: float, faithful: bool) -> str:
    """Return indicator based on faithfulness score."""
    if score >= 0.8:
        indicator = "🟢 Excellent"
    elif score >= 0.6:
        indicator = "🟡 Moderate"
    else:
        indicator = "🔴 Low"

    result = f"{indicator} ({score:.1%})"
    if not faithful:
        result += " ⚠️ Contains potential hallucinations"
    return result


def format_sources(sources: list) -> str:
    """Format source documents as markdown."""
    if not sources:
        return "No sources retrieved."

    md = "## 📚 Retrieved Sources\n\n"
    for i, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        score = source.get("score", 0.0)
        text = source.get("text", "")[:300]

        home_team = metadata.get("home_team", "Unknown")
        away_team = metadata.get("away_team", "Unknown")
        date = metadata.get("date", "Unknown")
        league = metadata.get("league", "Unknown")

        md += f"### Source {i} (Similarity: {score:.3f})\n\n"
        md += f"**Match:** {home_team} vs {away_team}  \n"
        md += f"**Date:** {date} | **League:** {league}  \n\n"
        md += f"**Preview:** {text}...\n\n"
        md += "---\n\n"

    return md


def process_question(
    question: str, provider: str, api_key: str
) -> Tuple[str, str, str]:
    """Process user question through RAG pipeline."""
    if not question.strip():
        return "Please enter a question.", "", ""

    try:
        # Initialize pipeline if provider changed
        if provider != current_provider or api_key != current_api_key:
            if not initialize_pipeline(provider, api_key):
                return "Error: Failed to initialize LLM provider", "", ""

        if pipeline is None:
            if not initialize_pipeline(provider, api_key):
                return "Error: Failed to initialize pipeline", "", ""

        logger.info(f"Processing: {question}")
        result = pipeline.query(question, top_k=5)

        answer = result["answer"]
        faithfulness = result["faithfulness"]
        sources = result["source_nodes"]

        faith_text = format_faithfulness_indicator(
            faithfulness["faithfulness_score"], faithfulness["faithful"]
        )

        if not faithfulness["faithful"] and faithfulness["hallucinated_numbers"]:
            faith_text += (
                f"\n\n**Hallucinated numbers:** {faithfulness['hallucinated_numbers']}"
            )

        if faithfulness["valid_numbers"]:
            faith_text += f"\n**Valid numbers:** {faithfulness['valid_numbers']}"

        sources_md = format_sources(sources)

        return answer, faith_text, sources_md

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"Error: {str(e)}", "N/A", "Error retrieving sources"


# Load prompt for UI info
prompts = load_prompt()

# Gradio Interface
with gr.Blocks(title="Football RAG Intelligence", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # ⚽ Football RAG Intelligence

    Ask questions about **Eredivisie** and **Championship** matches using our RAG system.

    **How to use:**
    1. Select your LLM provider below
    2. Paste your API key if using a cloud provider (optional for local Ollama)
    3. Ask your question
    4. Get faithful answers grounded in match data
    """)

    with gr.Row():
        with gr.Column(scale=2):
            provider_dropdown = gr.Dropdown(
                choices=[
                    "Ollama (Local)",
                    "Claude (Anthropic)",
                    "GPT-4o (OpenAI)",
                    "Gemini",
                ],
                value="Ollama (Local)",
                label="🤖 LLM Provider",
                info="Choose your LLM. Ollama is free but requires local setup.",
            )
        with gr.Column(scale=3):
            api_key_input = gr.Textbox(
                label="🔑 API Key",
                placeholder="Leave empty for Ollama, paste key for cloud providers",
                type="password",
                info="Your API key is never stored, only used in memory for this session.",
            )

    with gr.Row():
        with gr.Column(scale=4):
            question_input = gr.Textbox(
                label="💬 Your Question",
                placeholder="E.g., 'Which teams had high xG?'",
                lines=2,
                info="Ask about match statistics, team performance, player data, etc.",
            )
        with gr.Column(scale=1):
            submit_btn = gr.Button("🔍 Ask", variant="primary", size="lg")

    answer_output = gr.Textbox(
        label="📝 Answer",
        lines=6,
        interactive=False,
        info="Faithful answer grounded in retrieved match data",
    )
    faithfulness_output = gr.Markdown(label="✅ Faithfulness Check")
    sources_output = gr.Markdown(label="📚 Source Documents")

    def map_provider(display_name: str) -> str:
        """Map Gradio display name to provider name."""
        mapping = {
            "Ollama (Local)": "ollama",
            "Claude (Anthropic)": "anthropic",
            "GPT-4o (OpenAI)": "openai",
            "Gemini": "gemini",
        }
        return mapping.get(display_name, "ollama")

    submit_btn.click(
        fn=lambda q, p, k: process_question(q, map_provider(p), k),
        inputs=[question_input, provider_dropdown, api_key_input],
        outputs=[answer_output, faithfulness_output, sources_output],
    )

    question_input.submit(
        fn=lambda q, p, k: process_question(q, map_provider(p), k),
        inputs=[question_input, provider_dropdown, api_key_input],
        outputs=[answer_output, faithfulness_output, sources_output],
    )

    gr.Markdown("""
    ---
    ## 💰 Cost Estimation

    Testing all features with your API key will cost **< $0.50**:
    - **Claude 3.5 Haiku:** ~$0.0001 per query
    - **GPT-4o mini:** ~$0.00015 per query
    - **Gemini 1.5 Flash:** ~$0.00005 per query

    ## ✅ How it Works

    This RAG system:
    1. Retrieves relevant match documents from ChromaDB
    2. Sends them as context to your chosen LLM
    3. Validates responses against source data to detect hallucinations
    4. Shows you the faithfulness score and source documents

    **Why it matters:** Traditional LLMs can hallucinate. Our system prevents this by only allowing answers grounded in real match data.
    """)


# FastAPI app
app = FastAPI(title="Football RAG Intelligence", version="1.0.0")
app.add_middleware(ObservabilityMiddleware)


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "football-rag-intelligence"})


@app.get("/metrics")
async def get_metrics() -> JSONResponse:
    """Metrics endpoint."""
    snapshot = metrics.snapshot()
    return JSONResponse(snapshot)


# Mount Gradio
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Football RAG Intelligence...")
    uvicorn.run(app, host="0.0.0.0", port=7860)
