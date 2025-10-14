"""Custom embedding wrapper for LlamaIndex compatibility."""

from typing import List
from llama_index.core.embeddings import BaseEmbedding
from sentence_transformers import SentenceTransformer


class VectorStoreEmbedding(BaseEmbedding):
    """Wrapper around SentenceTransformer for LlamaIndex with NumPy 2.x compatibility."""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        super().__init__()
        self._model = SentenceTransformer(model_name)

    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embedding = self._model.encode(
            query,
            convert_to_tensor=True,
            normalize_embeddings=False
        )
        return embedding.cpu().tolist()

    def _get_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self._model.encode(
            text,
            convert_to_tensor=True,
            normalize_embeddings=False
        )
        return embedding.cpu().tolist()

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self._model.encode(
            texts,
            convert_to_tensor=True,
            normalize_embeddings=False
        )
        return embeddings.cpu().tolist()

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async version - falls back to sync (sentence-transformers doesn't support async)."""
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Async version - falls back to sync (sentence-transformers doesn't support async)."""
        return self._get_text_embedding(text)
