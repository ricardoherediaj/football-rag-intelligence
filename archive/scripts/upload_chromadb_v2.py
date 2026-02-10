"""Upload ChromaDB v2 tarball to HuggingFace Dataset"""
from huggingface_hub import HfApi

api = HfApi()

# Upload the v2 tarball (to bypass HF Spaces cache)
api.upload_file(
    path_or_fileobj="football_matches_chromadb_v2.tar.gz",
    path_in_repo="football_matches_chromadb_v2.tar.gz",
    repo_id="rheredia8/football-rag-chromadb",
    repo_type="dataset",
)

print("✅ ChromaDB v2 tarball uploaded successfully!")
