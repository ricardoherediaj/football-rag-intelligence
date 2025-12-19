"""
HuggingFace Spaces Entry Point for Football RAG Intelligence
Launches the dual-mode Gradio interface (text analysis + visualizations)

Downloads ChromaDB from HF Dataset on first launch.
"""
import sys
import logging
import tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Constants
CHROMA_DATA_DIR = PROJECT_ROOT / "data" / "chroma"
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

        # Extract archive
        logger.info("📂 Extracting ChromaDB archive...")
        CHROMA_DATA_DIR.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=CHROMA_DATA_DIR.parent)

        logger.info("✅ ChromaDB downloaded and extracted successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download ChromaDB: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Starting Football RAG Intelligence for Hugging Face Spaces...")

    # Download ChromaDB first (crucial!)
    if not download_chromadb_if_needed():
        logger.error("Failed to initialize ChromaDB. Exiting.")
        exit(1)

    # Import and launch the demo (after ChromaDB is ready)
    from football_rag.app.main import demo

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # HF Spaces handles public URL
    )
