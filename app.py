"""
HuggingFace Spaces Entry Point for Football RAG Intelligence
Launches the dual-mode Gradio interface (text analysis + visualizations)
"""
import sys
from pathlib import Path

# Add src to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import and launch the demo
from football_rag.app.main import demo

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # HF Spaces handles public URL
    )
