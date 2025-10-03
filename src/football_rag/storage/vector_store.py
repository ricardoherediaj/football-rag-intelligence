"""
ChromaDB wrapper for vector storage with sentence-transformers embeddings.

This module provides a VectorStore class that manages football match data in ChromaDB
with automatic embedding generation and metadata-aware retrieval.
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Literal
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


ChunkType = Literal["match_summary", "player_events", "shots_analysis"]


class VectorStore:
    """
    ChromaDB wrapper for football match vector storage.

    Features:
    - Automatic embedding generation with sentence-transformers
    - Match-level chunking with rich metadata
    - Metadata filtering for precise retrieval
    - Support for WhoScored and Fotmob data sources

    Args:
        collection_name: Name of the ChromaDB collection
        embedding_model: Sentence-transformers model name (default: all-mpnet-base-v2)
        persist_directory: Directory for ChromaDB persistence (default: ./data/chroma)
        host: ChromaDB host (for client-server mode)
        port: ChromaDB port (for client-server mode)

    Example:
        >>> store = VectorStore()
        >>> store.add_documents(
        ...     documents=["Match summary text..."],
        ...     metadatas=[{"home_team": "Ajax", "away_team": "PSV"}],
        ...     ids=["match_summary_unified_match_001"]
        ... )
        >>> results = store.search("Ajax attacking play", k=5)
    """

    def __init__(
        self,
        collection_name: str = "football_matches_eredivisie_2025",
        embedding_model: str = "all-mpnet-base-v2",
        persist_directory: Optional[str] = "./data/chroma",
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """Initialize VectorStore with ChromaDB client and embedding model."""
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")

        # Initialize ChromaDB client
        if host and port:
            # Client-server mode (for Docker)
            logger.info(f"Connecting to ChromaDB server at {host}:{port}")
            self.client = chromadb.HttpClient(host=host, port=port)
        else:
            # Local persistent mode
            logger.info(f"Using persistent ChromaDB at {persist_directory}")
            self.client = chromadb.PersistentClient(path=persist_directory)

        # Get or create collection
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Football match data with semantic search"}
        )
        logger.info(f"Collection '{collection_name}' ready with {self.collection.count()} documents")

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """
        Add documents to the vector store with automatic embedding generation.

        Args:
            documents: List of text documents to embed and store
            metadatas: List of metadata dicts (one per document)
            ids: List of unique document IDs

        Raises:
            ValueError: If list lengths don't match

        Example:
            >>> store.add_documents(
            ...     documents=["Match: Ajax vs PSV..."],
            ...     metadatas=[{
            ...         "chunk_type": "match_summary",
            ...         "home_team": "Ajax",
            ...         "away_team": "PSV",
            ...         "league": "Eredivisie",
            ...         "season": "2025-2026"
            ...     }],
            ...     ids=["match_summary_unified_match_001"]
            ... )
        """
        if not (len(documents) == len(metadatas) == len(ids)):
            raise ValueError(
                f"Length mismatch: documents={len(documents)}, "
                f"metadatas={len(metadatas)}, ids={len(ids)}"
            )

        if not documents:
            logger.warning("No documents to add")
            return

        logger.info(f"Generating embeddings for {len(documents)} documents...")

        # Generate embeddings as PyTorch tensors (avoids NumPy compatibility issues)
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_tensor=True,  # Return as PyTorch tensor
            normalize_embeddings=False
        )

        # Convert to list directly (bypasses NumPy ABI issues)
        embeddings_list = embeddings.cpu().tolist()

        # Add ingestion timestamp to metadata (timezone-aware)
        timestamp = datetime.now(timezone.utc).isoformat()
        for metadata in metadatas:
            metadata["ingestion_timestamp"] = timestamp

        # Store in ChromaDB
        logger.info(f"Storing {len(documents)} documents in ChromaDB...")
        self.collection.add(
            documents=documents,
            embeddings=embeddings_list,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Successfully added {len(documents)} documents. Total: {self.collection.count()}")

    def search(
        self,
        query: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using semantic similarity.

        Args:
            query: Search query text
            k: Number of results to return
            where: Metadata filter (ChromaDB where syntax)
            where_document: Document content filter (ChromaDB where_document syntax)

        Returns:
            List of result dicts with keys: id, document, metadata, distance

        Example:
            >>> # Simple search
            >>> results = store.search("Bergwijn shot accuracy", k=5)

            >>> # Search with metadata filter
            >>> results = store.search(
            ...     "attacking play",
            ...     k=5,
            ...     where={"home_team": "Ajax", "chunk_type": "match_summary"}
            ... )
        """
        logger.info(f"Searching for: '{query}' (k={k})")

        # Generate query embedding as PyTorch tensor
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_tensor=True,
            normalize_embeddings=False
        )

        # Convert to list (bypasses NumPy issues)
        query_embedding_list = query_embedding.cpu().tolist()

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=k,
            where=where,
            where_document=where_document,
        )

        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                })

        logger.info(f"Found {len(formatted_results)} results")
        return formatted_results

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.

        Args:
            doc_id: Document ID

        Returns:
            Dict with id, document, metadata or None if not found
        """
        results = self.collection.get(ids=[doc_id])

        if results['ids']:
            return {
                'id': results['ids'][0],
                'document': results['documents'][0],
                'metadata': results['metadatas'][0],
            }
        return None

    def delete(self, ids: List[str]) -> None:
        """
        Delete documents by IDs.

        Args:
            ids: List of document IDs to delete
        """
        logger.info(f"Deleting {len(ids)} documents...")
        self.collection.delete(ids=ids)
        logger.info(f"Deleted. Total documents: {self.collection.count()}")

    def count(self) -> int:
        """Get total number of documents in collection."""
        return self.collection.count()

    def reset(self) -> None:
        """
        Delete all documents in the collection.

        WARNING: This operation cannot be undone!
        """
        logger.warning(f"Resetting collection '{self.collection_name}'...")
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Football match data with semantic search"}
        )
        logger.info("Collection reset complete")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Dict with count, collection_name, embedding_model
        """
        # Get model name (compatible with different sentence-transformers versions)
        try:
            model_name = self.embedding_model.get_config_dict()['model_name_or_path']
        except (AttributeError, KeyError):
            # Fallback for newer versions
            model_name = getattr(self.embedding_model, 'model_name_or_path', 'all-mpnet-base-v2')

        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "embedding_model": model_name,
            "embedding_dimension": self.embedding_dim,
        }