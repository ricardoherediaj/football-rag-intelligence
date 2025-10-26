#!/usr/bin/env python3
"""Upload ChromaDB export to Hugging Face Dataset.

This script uploads the local ChromaDB tar.gz file to the HF Dataset
so that HF Spaces can download pre-computed embeddings.
"""

from pathlib import Path
from huggingface_hub import HfApi

def upload_chromadb():
    """Upload ChromaDB export to HF Dataset."""

    # Paths
    local_file = Path("data/football_matches_chromadb.tar.gz")
    repo_id = "rheredia8/football-rag-chromadb"

    # Verify file exists
    if not local_file.exists():
        raise FileNotFoundError(f"ChromaDB export not found: {local_file}")

    file_size_kb = local_file.stat().st_size / 1024
    print(f"📦 Uploading ChromaDB export...")
    print(f"   File: {local_file}")
    print(f"   Size: {file_size_kb:.1f} KB")
    print(f"   Destination: {repo_id}")

    # Upload to HF
    api = HfApi()
    api.upload_file(
        path_or_fileobj=str(local_file),
        path_in_repo="football_matches_chromadb.tar.gz",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Update ChromaDB to v1.1.1 with 53 matches"
    )

    print(f"✅ Upload complete!")
    print(f"   URL: https://huggingface.co/datasets/{repo_id}")


if __name__ == "__main__":
    upload_chromadb()
