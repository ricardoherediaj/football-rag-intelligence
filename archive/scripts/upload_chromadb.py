"""Upload ChromaDB tarball to HuggingFace Dataset"""
from huggingface_hub import HfApi

api = HfApi()

# Upload the tarball
api.upload_file(
    path_or_fileobj="football_matches_chromadb.tar.gz",
    path_in_repo="football_matches_chromadb.tar.gz",
    repo_id="rheredia8/football-rag-chromadb",
    repo_type="dataset",
)

print("✅ ChromaDB tarball uploaded successfully!")
