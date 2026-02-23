"""Entry point: uv run python -m football_rag.app

Launches the Streamlit UI. Equivalent to:
    streamlit run src/football_rag/app/main.py
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    main_path = Path(__file__).parent / "main.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(main_path)],
        check=True,
    )
