"""
Simple embedding model wrapper.
"""

from typing import List
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Simple wrapper for sentence transformers."""
    
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode texts to embeddings."""
        return self.model.encode(texts).tolist()