"""
ChromaDB wrapper for vector storage.
"""

import chromadb
from typing import List, Dict, Any


class VectorStore:
    """Simple ChromaDB wrapper."""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection("football_matches")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Add documents to the vector store."""
        # TODO: Generate embeddings and store
        pass
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        # TODO: Implement search
        pass