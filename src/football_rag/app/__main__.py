"""Entry point for running the Gradio UI as a module.

Usage:
    uv run python -m football_rag.app
"""

from football_rag.app.main import demo

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
