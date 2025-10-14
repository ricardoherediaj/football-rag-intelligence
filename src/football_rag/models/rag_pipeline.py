"""RAG pipeline with LlamaIndex orchestration."""

import logging
import re
from typing import List, Dict, Any

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
import chromadb

from football_rag.config.settings import settings
from football_rag.models.custom_embeddings import VectorStoreEmbedding

logger = logging.getLogger(__name__)

# Football-specific system prompt for anti-hallucination
FOOTBALL_RAG_SYSTEM_PROMPT = """You are a football analytics assistant specialized in football analytics.

CRITICAL RULES:
1. ONLY use information from the provided context documents
2. NEVER invent statistics, percentages, or numbers not in context
3. If asked about xG, cite EXACT xG values from context (format: "Team A: X.XX xG")
4. If information is not in context, say "Not available in provided matches"
5. Keep answers concise (2-3 sentences maximum)
6. Always cite which match the data comes from (e.g., "Team A vs Team B")

FORBIDDEN:
- Do NOT mention metrics like "verticality", "shot quality", or percentages unless explicitly in context
- Do NOT compare statistics from different matches
- Do NOT use prior football knowledge
- Do NOT invent team names or scores

Example:
Q: "Which teams had high xG?"
A: "Feyenoord had 2.44 xG (vs NAC Breda) and Fortuna Sittard had 2.34 xG (vs Go Ahead Eagles). These were the highest xG values in the provided matches."
"""


class FaithfulnessChecker:
    """Validate generated answers against source documents."""

    def extract_numbers(self, text: str) -> List[float]:
        """Extract all numeric values from text."""
        return [float(n) for n in re.findall(r'\d+\.?\d*', text)]

    def check_faithfulness(self, answer: str, sources: List[Dict]) -> Dict:
        """
        Verify answer numbers exist in source documents.

        Returns:
            {
                'faithful': bool,
                'hallucinated_numbers': List[float],
                'valid_numbers': List[float],
                'faithfulness_score': float (0.0-1.0)
            }
        """
        answer_numbers = set(self.extract_numbers(answer))

        # Extract numbers from sources
        source_numbers = set()
        for source in sources:
            source_numbers.update(self.extract_numbers(source['text']))
            # Add metadata numbers
            for key, val in source.get('metadata', {}).items():
                if isinstance(val, (int, float)):
                    source_numbers.add(float(val))

        hallucinated = answer_numbers - source_numbers
        valid = answer_numbers & source_numbers

        return {
            'faithful': len(hallucinated) == 0,
            'hallucinated_numbers': sorted(list(hallucinated)),
            'valid_numbers': sorted(list(valid)),
            'faithfulness_score': len(valid) / len(answer_numbers) if answer_numbers else 1.0
        }


class RAGPipeline:
    """RAG pipeline orchestrated by LlamaIndex."""

    def __init__(self):
        """Initialize LlamaIndex components."""
        logger.info("Initializing RAG pipeline with LlamaIndex...")

        # Embeddings (custom wrapper with NumPy 2.x compatibility)
        LlamaSettings.embed_model = VectorStoreEmbedding(
            model_name=settings.models.embedding_model
        )

        # LLM
        LlamaSettings.llm = Ollama(
            model=settings.models.llm_model,
            base_url="http://localhost:11434",
            request_timeout=120.0,
            temperature=settings.models.temperature,
            additional_kwargs={
                "num_ctx": 3072,  # Context window optimized for 8GB RAM systems
                "num_predict": 256,  # Max tokens to generate
                "top_k": 40,
                "top_p": 0.9,
            }
        )

        # ChromaDB
        chroma_client = chromadb.HttpClient(
            host=settings.database.chroma_host,
            port=settings.database.chroma_port
        )
        collection = chroma_client.get_collection("football_matches_eredivisie_2025")
        vector_store = ChromaVectorStore(chroma_collection=collection)

        # Index
        self.index = VectorStoreIndex.from_vector_store(vector_store)
        logger.info("✓ RAG pipeline ready")

    def query(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Query the RAG pipeline."""
        logger.info(f"Query: {question}")

        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)

        return {
            "answer": str(response),
            "source_nodes": [
                {
                    "text": node.node.text,
                    "score": node.score,
                    "metadata": node.node.metadata
                }
                for node in response.source_nodes
            ]
        }

    @property
    def retriever(self):
        """Expose LlamaIndex retriever for evaluation."""
        return self.index.as_retriever(similarity_top_k=5)

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents without generation."""
        retriever = self.index.as_retriever(similarity_top_k=k)
        nodes = retriever.retrieve(query)

        return [
            {
                "text": node.node.text,
                "score": node.score,
                "metadata": node.node.metadata
            }
            for node in nodes
        ]
