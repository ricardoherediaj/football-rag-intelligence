"""Test LlamaIndex compatibility with ChromaDB Docker."""

import pytest
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings


def test_chromadb_docker_connection():
    """Test connection to ChromaDB Docker container."""

    # Connect to Docker ChromaDB
    chroma_client = chromadb.HttpClient(
        host="localhost",
        port=8000
    )

    # List collections
    collections = chroma_client.list_collections()
    print(f"\nCollections: {[c.name for c in collections]}")

    # Get existing collection
    collection = chroma_client.get_or_create_collection(
        name="football_matches_eredivisie_2025"
    )

    # Check count
    count = collection.count()
    print(f"Document count: {count}")

    assert count >= 0, "Should be able to query collection"


def test_llamaindex_vector_store():
    """Test LlamaIndex ChromaVectorStore wrapper."""

    # Connect to ChromaDB
    chroma_client = chromadb.HttpClient(host="localhost", port=8000)
    collection = chroma_client.get_or_create_collection(
        "football_matches_eredivisie_2025"
    )

    # Create LlamaIndex wrapper
    vector_store = ChromaVectorStore(chroma_collection=collection)

    assert vector_store is not None
    print("\n✅ ChromaVectorStore created successfully")


def test_embedding_model():
    """Test HuggingFace embedding model (same as current setup)."""

    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )

    # Test embedding
    text = "Ajax dominated possession with 58%"
    embedding = embed_model.get_text_embedding(text)

    assert len(embedding) == 768, "Should be 768 dimensions"
    print(f"\n✅ Embedding model working (dim: {len(embedding)})")


def test_ollama_llm():
    """Test Ollama LLM connection."""

    llm = Ollama(
        model="llama3.2:1b",
        base_url="http://localhost:11434"
    )

    # Simple query
    response = llm.complete("What is 2+2?")

    assert response is not None
    print(f"\n✅ Ollama LLM working")
    print(f"Response: {response.text[:100]}")


def test_llamaindex_settings():
    """Test LlamaIndex global settings."""

    # Set global settings
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
    Settings.llm = Ollama(model="llama3.2:1b")

    print("\n✅ LlamaIndex Settings configured")
    print(f"Embed model: {Settings.embed_model}")
    print(f"LLM: {Settings.llm}")


if __name__ == "__main__":
    print("=== Testing LlamaIndex Setup ===\n")

    try:
        test_chromadb_docker_connection()
        test_llamaindex_vector_store()
        test_embedding_model()
        test_ollama_llm()
        test_llamaindex_settings()

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED - LlamaIndex ready!")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
