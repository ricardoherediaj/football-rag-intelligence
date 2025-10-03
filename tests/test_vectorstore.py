"""
Test suite for VectorStore functionality.

Tests both local persistent mode and Docker server mode for ChromaDB.
Verifies embedding generation, document ingestion, and semantic search.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_rag.storage.vector_store import VectorStore


class TestVectorStoreLocal:
    """Test VectorStore with local persistent storage."""

    @pytest.fixture
    def vector_store(self, tmp_path):
        """Create VectorStore with temporary directory."""
        return VectorStore(
            collection_name="test_collection_local",
            persist_directory=str(tmp_path / "chroma_test"),
        )

    def test_initialization(self, vector_store):
        """Test VectorStore initializes correctly."""
        assert vector_store.collection_name == "test_collection_local"
        assert vector_store.embedding_dim == 768  # all-mpnet-base-v2 dimension
        assert vector_store.count() == 0

    def test_add_documents(self, vector_store):
        """Test adding documents with metadata."""
        documents = [
            "Ajax defeated PSV 3-1 in a thrilling Eredivisie match. Bergwijn scored twice.",
            "Feyenoord drew 2-2 with Utrecht in a competitive game.",
        ]
        metadatas = [
            {
                "chunk_type": "match_summary",
                "home_team": "Ajax",
                "away_team": "PSV",
                "league": "Eredivisie",
                "season": "2025-2026",
                "raw_data_path": "whoscored/eredivisie/2025-2026/match_001.json",
            },
            {
                "chunk_type": "match_summary",
                "home_team": "Feyenoord",
                "away_team": "Utrecht",
                "league": "Eredivisie",
                "season": "2025-2026",
                "raw_data_path": "whoscored/eredivisie/2025-2026/match_002.json",
            },
        ]
        ids = ["test_match_001", "test_match_002"]

        vector_store.add_documents(documents, metadatas, ids)

        assert vector_store.count() == 2

    def test_search_basic(self, vector_store):
        """Test basic semantic search."""
        # Add test data
        documents = [
            "Ajax defeated PSV 3-1. Bergwijn scored twice and provided an assist.",
            "Feyenoord drew 2-2 with Utrecht. Both teams had excellent chances.",
        ]
        metadatas = [
            {"home_team": "Ajax", "away_team": "PSV"},
            {"home_team": "Feyenoord", "away_team": "Utrecht"},
        ]
        ids = ["match_001", "match_002"]

        vector_store.add_documents(documents, metadatas, ids)

        # Search
        results = vector_store.search("Bergwijn goals", k=2)

        assert len(results) == 2
        assert results[0]["id"] == "match_001"  # Should rank Ajax match first
        assert "Bergwijn" in results[0]["document"]
        assert "distance" in results[0]

    def test_search_with_metadata_filter(self, vector_store):
        """Test search with metadata filtering."""
        # Add test data
        documents = [
            "Ajax won 3-1 with excellent attacking play.",
            "PSV lost 1-3 in a defensive struggle.",
        ]
        metadatas = [
            {"home_team": "Ajax", "away_team": "PSV", "chunk_type": "match_summary"},
            {"home_team": "PSV", "away_team": "Ajax", "chunk_type": "match_summary"},
        ]
        ids = ["match_001", "match_002"]

        vector_store.add_documents(documents, metadatas, ids)

        # Search with filter
        results = vector_store.search(
            "attacking play", k=5, where={"home_team": "Ajax"}
        )

        assert len(results) == 1
        assert results[0]["id"] == "match_001"
        assert results[0]["metadata"]["home_team"] == "Ajax"

    def test_get_by_id(self, vector_store):
        """Test retrieving document by ID."""
        documents = ["Ajax defeated PSV 3-1."]
        metadatas = [{"home_team": "Ajax"}]
        ids = ["match_001"]

        vector_store.add_documents(documents, metadatas, ids)

        result = vector_store.get_by_id("match_001")

        assert result is not None
        assert result["id"] == "match_001"
        assert "Ajax" in result["document"]
        assert result["metadata"]["home_team"] == "Ajax"

    def test_get_by_id_not_found(self, vector_store):
        """Test get_by_id returns None for non-existent ID."""
        result = vector_store.get_by_id("non_existent")
        assert result is None

    def test_delete_documents(self, vector_store):
        """Test deleting documents."""
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        metadatas = [{}, {}, {}]
        ids = ["id_1", "id_2", "id_3"]

        vector_store.add_documents(documents, metadatas, ids)
        assert vector_store.count() == 3

        vector_store.delete(["id_1", "id_2"])
        assert vector_store.count() == 1

    def test_reset_collection(self, vector_store):
        """Test resetting collection."""
        documents = ["Doc 1", "Doc 2"]
        metadatas = [{}, {}]
        ids = ["id_1", "id_2"]

        vector_store.add_documents(documents, metadatas, ids)
        assert vector_store.count() == 2

        vector_store.reset()
        assert vector_store.count() == 0

    def test_get_stats(self, vector_store):
        """Test getting collection statistics."""
        stats = vector_store.get_stats()

        assert "collection_name" in stats
        assert "document_count" in stats
        assert "embedding_model" in stats
        assert "embedding_dimension" in stats

        assert stats["collection_name"] == "test_collection_local"
        assert stats["document_count"] == 0
        assert stats["embedding_dimension"] == 768

    def test_empty_documents(self, vector_store):
        """Test adding empty document list."""
        vector_store.add_documents([], [], [])
        assert vector_store.count() == 0

    def test_length_mismatch_error(self, vector_store):
        """Test error when list lengths don't match."""
        with pytest.raises(ValueError, match="Length mismatch"):
            vector_store.add_documents(
                documents=["Doc 1", "Doc 2"],
                metadatas=[{}],  # Wrong length
                ids=["id_1", "id_2"],
            )


class TestVectorStoreDocker:
    """Test VectorStore with Docker ChromaDB server."""

    @pytest.fixture
    def vector_store(self):
        """Create VectorStore connected to Docker ChromaDB."""
        try:
            return VectorStore(
                collection_name="test_collection_docker",
                host="localhost",
                port=8000,
            )
        except Exception as e:
            pytest.skip(f"ChromaDB Docker not available: {e}")

    def test_docker_connection(self, vector_store):
        """Test connection to Docker ChromaDB."""
        assert vector_store.collection_name == "test_collection_docker"
        assert vector_store.count() >= 0  # Should not error

    def test_add_and_search_docker(self, vector_store):
        """Test adding and searching in Docker mode."""
        # Clean collection first
        vector_store.reset()

        documents = [
            "PSV's attacking midfielder showed excellent vision. Three key passes led to goals.",
        ]
        metadatas = [
            {
                "chunk_type": "player_events",
                "player_name": "Test Player",
                "team_name": "PSV",
                "raw_data_path": "test/path.json",
            },
        ]
        ids = ["test_player_001"]

        vector_store.add_documents(documents, metadatas, ids)

        # Search
        results = vector_store.search("attacking midfielder", k=1)

        assert len(results) == 1
        assert results[0]["id"] == "test_player_001"
        assert results[0]["metadata"]["player_name"] == "Test Player"

        # Clean up
        vector_store.reset()

    def test_metadata_filter_docker(self, vector_store):
        """Test metadata filtering in Docker mode."""
        # Clean collection first
        vector_store.reset()

        documents = ["Ajax match data", "PSV match data"]
        metadatas = [
            {"team_name": "Ajax", "chunk_type": "match_summary"},
            {"team_name": "PSV", "chunk_type": "match_summary"},
        ]
        ids = ["ajax_001", "psv_001"]

        vector_store.add_documents(documents, metadatas, ids)

        # Search with filter
        results = vector_store.search("match", k=5, where={"team_name": "Ajax"})

        assert len(results) == 1
        assert results[0]["id"] == "ajax_001"

        # Clean up
        vector_store.reset()


class TestVectorStoreIntegration:
    """Integration tests simulating real usage."""

    @pytest.fixture
    def vector_store(self, tmp_path):
        """Create VectorStore for integration tests."""
        return VectorStore(
            collection_name="test_integration",
            persist_directory=str(tmp_path / "chroma_integration"),
        )

    def test_football_match_workflow(self, vector_store):
        """Test realistic football match data workflow."""
        # Simulate match summary chunks
        documents = [
            """
            Match: Ajax vs PSV
            Date: 2025-09-15
            League: Eredivisie
            Score: 3-1

            Ajax dominated possession with 58% vs 42%. They created 15 shots vs 10 from PSV.
            The xG favored Ajax (1.8 vs 1.2), reflecting better quality chances.
            Bergwijn scored twice in the 23rd and 67th minute. Taylor made one goal for PSV.
            """,
            """
            Match: Feyenoord vs Utrecht
            Date: 2025-09-16
            League: Eredivisie
            Score: 2-2

            A balanced match with both teams having 50% possession. Feyenoord had 12 shots,
            Utrecht 11. The xG was almost equal (1.5 vs 1.4). Goals from Gimenez and Timber
            for Feyenoord, Booth and Jensen for Utrecht.
            """,
        ]

        metadatas = [
            {
                "chunk_type": "match_summary",
                "unified_match_id": "unified_match_001",
                "home_team": "Ajax",
                "away_team": "PSV",
                "league": "Eredivisie",
                "season": "2025-2026",
                "match_date": "2025-09-15",
                "raw_data_path": "whoscored/eredivisie/2025-2026/match_1903733.json",
                "fotmob_data_path": "fotmob/eredivisie/2025-2026/match_4815204.json",
            },
            {
                "chunk_type": "match_summary",
                "unified_match_id": "unified_match_002",
                "home_team": "Feyenoord",
                "away_team": "Utrecht",
                "league": "Eredivisie",
                "season": "2025-2026",
                "match_date": "2025-09-16",
                "raw_data_path": "whoscored/eredivisie/2025-2026/match_1903734.json",
                "fotmob_data_path": "fotmob/eredivisie/2025-2026/match_4815205.json",
            },
        ]

        ids = ["match_summary_unified_match_001", "match_summary_unified_match_002"]

        # Ingest
        vector_store.add_documents(documents, metadatas, ids)

        # Query 1: Who scored for Ajax?
        results = vector_store.search("Who scored for Ajax vs PSV?", k=1)
        assert len(results) == 1
        assert "Bergwijn" in results[0]["document"]
        assert results[0]["metadata"]["home_team"] == "Ajax"

        # Query 2: Possession stats
        results = vector_store.search("possession statistics", k=2)
        assert len(results) == 2
        assert any("58%" in r["document"] for r in results)

        # Query 3: Filter by team
        results = vector_store.search(
            "match result", k=5, where={"home_team": "Feyenoord"}
        )
        assert len(results) == 1
        assert results[0]["metadata"]["home_team"] == "Feyenoord"

        # Query 4: Check raw_data_path exists (critical for visualizations)
        result = vector_store.get_by_id("match_summary_unified_match_001")
        assert result is not None
        assert "raw_data_path" in result["metadata"]
        assert "whoscored" in result["metadata"]["raw_data_path"]
        assert "fotmob_data_path" in result["metadata"]
        assert "fotmob" in result["metadata"]["fotmob_data_path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
