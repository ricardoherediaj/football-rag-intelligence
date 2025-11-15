"""
Hugging Face Spaces entry point for Football RAG Intelligence
Simplified version optimized for HF Spaces deployment
"""

import os
import sys
import logging
from pathlib import Path
import tarfile
from typing import Tuple
from huggingface_hub import hf_hub_download
import gradio as gr

# Add src to Python path for module imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
CHROMA_DATA_DIR = Path("./data/chroma")
HF_DATASET_REPO = "rheredia8/football-rag-chromadb"
CHROMA_ARCHIVE = "football_matches_chromadb.tar.gz"


def download_chromadb_if_needed():
    """Download ChromaDB from HF Dataset if not exists locally."""
    if CHROMA_DATA_DIR.exists() and any(CHROMA_DATA_DIR.iterdir()):
        logger.info("✓ ChromaDB already exists locally")
        return True

    logger.info("📦 Downloading ChromaDB from Hugging Face Dataset...")

    try:
        # Download from HF Dataset
        logger.info(f"Fetching from {HF_DATASET_REPO}...")
        archive_path = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename=CHROMA_ARCHIVE,
            repo_type="dataset",
        )

        # Extract archive directly to data/chroma
        logger.info("📂 Extracting ChromaDB archive...")

        # Create target directory
        CHROMA_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Extract directly to target, stripping leading ./
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                # Strip leading ./ from member names
                if member.name.startswith("./"):
                    member.name = member.name[2:]
                if member.name:  # Skip empty paths
                    tar.extract(member, path=str(CHROMA_DATA_DIR))

        logger.info(f"✓ ChromaDB extracted to {CHROMA_DATA_DIR}")

        logger.info("✓ ChromaDB ready with all 53 matches!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download ChromaDB: {e}")
        return False


def format_faithfulness_indicator(score: float, faithful: bool) -> str:
    """Return visual indicator based on faithfulness score."""
    if score >= 0.8:
        indicator = "🟢 Excellent"
    elif score >= 0.6:
        indicator = "🟡 Moderate"
    else:
        indicator = "🔴 Low"

    result = f"{indicator} ({score:.1%})"
    if not faithful:
        result += " ⚠️ **Potential hallucinations detected**"
    return result


def format_sources(sources: list) -> str:
    """Format source documents as markdown."""
    if not sources:
        return "⚠️ No sources retrieved."

    md = "## 📚 Retrieved Sources\n\n"
    for i, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        score = source.get("score", 0.0)
        text = source.get("text", "")[:250]

        home_team = metadata.get("home_team", "Unknown")
        away_team = metadata.get("away_team", "Unknown")
        date = metadata.get("date", "Unknown")
        league = metadata.get("league", "Unknown")

        md += f"### Source {i} (Similarity: {score:.3f})\n\n"
        md += f"**Match:** {home_team} vs {away_team}  \n"
        md += f"**Date:** {date} | **League:** {league}  \n\n"
        md += f"> {text}...\n\n"
        md += "---\n\n"

    return md


def process_question(
    question: str, provider: str, api_key: str
) -> Tuple[str, str, str]:
    """Process user question through RAG pipeline."""
    if not question.strip():
        return "⚠️ Please enter a question.", "", ""

    if not api_key.strip():
        return (
            f"⚠️ Please enter your API key for {provider}.\n\n"
            f"Get your key from:\n"
            f"- Anthropic: https://console.anthropic.com/\n"
            f"- OpenAI: https://platform.openai.com/api-keys\n"
            f"- Gemini: https://makersuite.google.com/app/apikey",
            "",
            "",
        )

    try:
        # Import here to avoid loading before ChromaDB is ready
        from football_rag.models.rag_pipeline import RAGPipeline

        # Map display name to provider code
        provider_map = {
            "Claude (Anthropic)": "anthropic",
            "GPT-4o (OpenAI)": "openai",
            "Gemini": "gemini",
        }
        provider_code = provider_map.get(provider, "anthropic")

        logger.info(f"🔍 Processing question with {provider_code}")

        # Initialize pipeline with local ChromaDB
        pipeline = RAGPipeline(
            provider=provider_code,
            api_key=api_key,
            chroma_persist_directory=str(CHROMA_DATA_DIR)
        )

        # Query
        result = pipeline.query(question, top_k=5)

        # Extract results
        answer = result["answer"]
        faithfulness = result["faithfulness"]
        sources = result.get("source_nodes", [])

        # Format faithfulness
        faith_score = faithfulness.get("faithfulness_score", 0.0)
        faith_status = faithfulness.get("faithful", True)
        faith_text = format_faithfulness_indicator(faith_score, faith_status)

        if not faith_status and faithfulness.get("hallucinated_numbers"):
            faith_text += (
                f"\n\n**Hallucinated numbers:** {faithfulness['hallucinated_numbers']}"
            )

        if faithfulness.get("valid_numbers"):
            faith_text += f"\n**Valid numbers:** {faithfulness['valid_numbers']}"

        # Format sources
        sources_md = format_sources(sources)

        logger.info(f"✓ Query processed successfully (faithfulness: {faith_score:.2%})")

        return answer, faith_text, sources_md

    except Exception as e:
        logger.error(f"❌ Error processing question: {e}", exc_info=True)
        error_msg = f"❌ Error: {str(e)}\n\nPlease check:\n"
        error_msg += "- API key is correct\n"
        error_msg += "- Provider is selected properly\n"
        error_msg += "- Question is valid"
        return error_msg, "N/A", "Error occurred"


def create_ui():
    """Create Gradio interface optimized for HF Spaces."""
    with gr.Blocks(
        title="⚽ Football RAG Intelligence",
        theme=gr.themes.Soft(primary_hue="green", secondary_hue="blue"),
        css="""
        .container { max-width: 1200px; margin: auto; }
        .warning { color: #ff6b6b; font-weight: bold; }
        """,
    ) as demo:
        gr.Markdown("""
        # ⚽ Football RAG Intelligence

        **AI-powered football match analysis with anti-hallucination validation**

        Ask questions about Eredivisie matches and get faithful answers grounded in real match data.

        🔒 **Privacy:** Your API key is NOT stored - only used for your current session.
        """)

        with gr.Row():
            with gr.Column(scale=2):
                provider = gr.Dropdown(
                    choices=["Claude (Anthropic)", "GPT-4o (OpenAI)", "Gemini"],
                    value="Claude (Anthropic)",
                    label="🤖 LLM Provider",
                    info="Select your preferred AI provider",
                )
            with gr.Column(scale=3):
                api_key = gr.Textbox(
                    type="password",
                    label="🔑 API Key",
                    placeholder="Enter your API key (sk-ant-... or sk-...)",
                    info="Not stored, only used for current session. Get yours from provider's website.",
                )

        with gr.Row():
            question = gr.Textbox(
                label="💬 Your Question",
                placeholder="Example: Which teams had high xG in recent matches?",
                lines=2,
                scale=4,
            )

        with gr.Row():
            submit_btn = gr.Button("🔍 Ask", variant="primary", size="lg", scale=1)
            clear_btn = gr.Button("🗑️ Clear", size="lg", scale=1)

        with gr.Row():
            answer_box = gr.Textbox(
                label="📝 Answer", lines=8, interactive=False, show_copy_button=True
            )

        with gr.Row():
            with gr.Column(scale=1):
                faithfulness_box = gr.Markdown(
                    label="✅ Faithfulness Score", value="*Awaiting query...*"
                )
            with gr.Column(scale=2):
                sources_box = gr.Markdown(
                    label="📚 Source Documents",
                    value="*Sources will appear here after your query*",
                )

        # Examples
        gr.Examples(
            examples=[
                ["Which teams had high xG?", "Claude (Anthropic)", ""],
                ["Tell me about Feyenoord's performance", "Claude (Anthropic)", ""],
                ["What were the highest scoring matches?", "Claude (Anthropic)", ""],
                ["Which teams use high pressing tactics?", "GPT-4o (OpenAI)", ""],
                ["Show me teams with good possession stats", "Gemini", ""],
            ],
            inputs=[question, provider, api_key],
            label="💡 Example Questions",
        )

        gr.Markdown("""
        ---

        ## 📊 Evaluation Metrics

        This RAG system has been evaluated with the following performance:

        - **Hit@5**: 80% (retrieval quality)
        - **MRR**: 0.750 (ranking quality)
        - **Faithfulness**: 96% (anti-hallucination)
        - **Relevancy**: 90% (answer quality)

        ## 💰 Cost Estimation

        Typical query costs (per question):
        - **Claude 3.5 Haiku:** ~$0.0001
        - **GPT-4o mini:** ~$0.00015
        - **Gemini 1.5 Flash:** ~$0.00005

        **Testing budget:** 100 queries ≈ $0.01-0.02

        ## 🔧 How It Works

        1. **Retrieval:** Searches ChromaDB vector database for relevant match documents
        2. **Augmentation:** Adds retrieved context to your question
        3. **Generation:** LLM generates answer grounded in context
        4. **Validation:** Checks if numbers in answer exist in source documents
        5. **Attribution:** Shows which matches support the answer

        ## 🔗 Links

        - **GitHub:** [football-rag-intelligence](https://github.com/your-username/football-rag-intelligence)
        - **Evaluation Report:** [Checkpoint Document](https://github.com/your-username/football-rag-intelligence/blob/main/docs/checkpoint_rag_evaluation_1819202025.md)
        - **License:** MIT
        """)

        # Event handlers
        submit_btn.click(
            fn=process_question,
            inputs=[question, provider, api_key],
            outputs=[answer_box, faithfulness_box, sources_box],
        )

        question.submit(
            fn=process_question,
            inputs=[question, provider, api_key],
            outputs=[answer_box, faithfulness_box, sources_box],
        )

        clear_btn.click(
            fn=lambda: (
                "",
                "*Awaiting query...*",
                "*Sources will appear here after your query*",
            ),
            inputs=[],
            outputs=[answer_box, faithfulness_box, sources_box],
        )

    return demo


if __name__ == "__main__":
    logger.info("🚀 Starting Football RAG Intelligence for Hugging Face Spaces...")

    # Download ChromaDB first (crucial!)
    if not download_chromadb_if_needed():
        logger.error("Failed to initialize ChromaDB. Exiting.")
        exit(1)

    # Create and launch Gradio interface
    demo = create_ui()
    demo.queue(max_size=20)  # Limit concurrent requests
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        share=False,  # HF Spaces handles public URL
    )
