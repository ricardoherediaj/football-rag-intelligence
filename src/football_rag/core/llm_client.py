"""
LLM call wrapper (skeleton) to centralize timeouts/retries later.
Why: one entrypoint to add resilience in Phase 2 without refactors.
"""

from typing import Any, Dict


def generate_with_llm(
    prompt: str, *, timeout_ms: int, max_retries: int, **kwargs: Dict[str, Any]
) -> str:
    raise NotImplementedError("Implement in Phase 2 (timeouts/retries/breaker)")
