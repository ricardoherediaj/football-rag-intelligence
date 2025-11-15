"""Simplified RAG pipeline with multi-provider LLM support (no LlamaIndex)."""

import logging
import re
import hashlib
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path

from football_rag.config.settings import settings
from football_rag.storage.vector_store import VectorStore
from football_rag.models.generate import generate_with_llm
from football_rag.prompts_loader import load_prompt

logger = logging.getLogger(__name__)


def check_faithfulness(answer: str, sources: List[Dict]) -> Dict:
    """Verify answer numbers exist in source documents."""
    answer_numbers = set(float(n) for n in re.findall(r"\d+\.?\d*", answer))

    source_numbers = set()
    for source in sources:
        source_numbers.update(
            float(n) for n in re.findall(r"\d+\.?\d*", source["text"])
        )
        for key, val in source.get("metadata", {}).items():
            if isinstance(val, (int, float)):
                source_numbers.add(float(val))

    hallucinated = answer_numbers - source_numbers
    valid = answer_numbers & source_numbers

    return {
        "faithful": len(hallucinated) == 0,
        "hallucinated_numbers": sorted(list(hallucinated)),
        "valid_numbers": sorted(list(valid)),
        "faithfulness_score": len(valid) / len(answer_numbers)
        if answer_numbers
        else 1.0,
    }


class RAGPipeline:
    """Simplified RAG pipeline with multi-provider LLM support."""

    def __init__(
        self,
        provider: str = "ollama",
        api_key: Optional[str] = None,
        chroma_persist_directory: Optional[str] = None,
    ):
        """Initialize RAG pipeline.

        Args:
            provider: LLM provider ('ollama', 'anthropic', 'openai', 'gemini')
            api_key: API key for cloud providers
            chroma_persist_directory: Path to local ChromaDB directory (overrides server mode)
        """
        logger.info(f"Initializing RAG pipeline with provider: {provider}")

        # Direct ChromaDB connection (no LlamaIndex overhead)
        if chroma_persist_directory:
            # Use local persistent ChromaDB
            self.vector_store = VectorStore(
                collection_name="football_matches_eredivisie_2025",
                persist_directory=chroma_persist_directory,
            )
        else:
            # Use ChromaDB server
            self.vector_store = VectorStore(
                collection_name="football_matches_eredivisie_2025",
                host=settings.database.chroma_host,
                port=settings.database.chroma_port,
            )

        self.provider = provider
        self.api_key = api_key

        # Load prompt profile
        self.prompts = load_prompt(settings.prompt_profile)

        # Setup cache
        self.cache_dir = Path("data/query_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ RAG pipeline ready")

    def _get_cache_key(self, question: str, top_k: int) -> str:
        """Generate cache key from question and provider."""
        key = f"{question.lower().strip()}_{top_k}_{self.provider}"
        return hashlib.md5(key.encode()).hexdigest()

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Query RAG pipeline with multi-provider LLM support."""
        # Check cache
        cache_key = self._get_cache_key(question, top_k)
        cache_path = self.cache_dir / f"{cache_key}.pkl"

        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    result = pickle.load(f)
                    logger.info(f"⚡ Cache hit: {question[:60]}...")
                    return result
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")

        # Retrieve context from ChromaDB
        logger.info(f"🔍 Retrieving context for: {question[:60]}...")
        results = self.vector_store.search(query=question, k=top_k)

        # Convert to source nodes format (for compatibility with existing code)
        source_nodes = [
            {
                "text": r["document"],
                "score": 1 - r["distance"] if r["distance"] else 1.0,
                "metadata": r["metadata"],
            }
            for r in results
        ]

        # Format context for LLM
        context = "\n\n".join(
            f"Source {i + 1}:\n{node['text']}" for i, node in enumerate(source_nodes)
        )
        llm_prompt = self.prompts["user_template"].format(
            context=context, question=question
        )

        # Generate with selected provider
        logger.info(f"🤖 Generating with {self.provider}...")
        answer = generate_with_llm(
            llm_prompt,
            provider=self.provider,
            api_key=self.api_key,
            system_prompt=self.prompts["system"],
            temperature=settings.models.temperature,
            max_tokens=512,
        )

        # Validate faithfulness
        faithfulness = check_faithfulness(answer, source_nodes)
        if not faithfulness["faithful"]:
            logger.warning(f"⚠️ Hallucinations: {faithfulness['hallucinated_numbers']}")

        result = {
            "answer": answer,
            "source_nodes": source_nodes,
            "faithfulness": faithfulness,
        }

        # Save to cache
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(result, f)
            logger.info("💾 Cached result")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

        return result

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents without generation."""
        results = self.vector_store.search(query=query, k=k)

        return [
            {
                "text": r["document"],
                "score": 1 - r["distance"] if r["distance"] else 1.0,
                "metadata": r["metadata"],
            }
            for r in results
        ]
