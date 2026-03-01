"""Simple LLM generation function supporting multiple providers."""

import os
from typing import Optional

import opik
from dotenv import load_dotenv
from football_rag.custom_logging import get_logger

load_dotenv()

logger = get_logger(__name__)


def generate_with_llm(
    prompt: str,
    provider: str = "ollama",
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 512,
) -> str:
    """Generate text using specified LLM provider.

    Args:
        prompt: User query/prompt
        provider: 'ollama', 'anthropic', 'openai', 'gemini', or 'cerebras'
        api_key: API key for cloud providers (required for non-Ollama)
        system_prompt: System instruction
        temperature: Sampling temperature (0-1)
        max_tokens: Max response length

    Returns:
        Generated text response
    """
    provider = provider.lower().strip()

    if provider == "ollama":
        return _generate_ollama(prompt, system_prompt, temperature, max_tokens)
    elif provider == "anthropic":
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        return _generate_anthropic(
            prompt, resolved_key, system_prompt, temperature, max_tokens
        )
    elif provider == "openai":
        return _generate_openai(prompt, api_key, system_prompt, temperature, max_tokens)
    elif provider == "gemini":
        return _generate_gemini(prompt, api_key, system_prompt, temperature, max_tokens)
    elif provider == "cerebras":
        return _generate_cerebras(
            prompt, api_key, system_prompt, temperature, max_tokens
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _generate_ollama(
    prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int
) -> str:
    """Generate using local Ollama."""
    import requests

    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": full_prompt,
                "temperature": temperature,
                "stream": False,
                "num_predict": max_tokens,
                "top_p": 0.85,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama not running. Start with: ollama serve")


@opik.track(name="llm_generation", tags=["provider:anthropic"])
def _generate_anthropic(
    prompt: str,
    api_key: Optional[str],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    """Generate using Anthropic Claude."""
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY required")

    try:
        import anthropic
    except ImportError:
        raise ImportError("Install anthropic: uv add anthropic")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt or "",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


@opik.track(name="llm_generation", tags=["provider:openai"])
def _generate_openai(
    prompt: str,
    api_key: Optional[str],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    """Generate using OpenAI GPT."""
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install openai: uv add openai")

    client = OpenAI(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


@opik.track(name="llm_generation", tags=["provider:gemini"])
def _generate_gemini(
    prompt: str,
    api_key: Optional[str],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    """Generate using Google Gemini."""
    if not api_key:
        raise ValueError("GEMINI_API_KEY required")

    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Install google-generativeai: uv add google-generativeai")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    response = model.generate_content(
        full_prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        },
    )
    return response.text.strip()


@opik.track(name="llm_generation", tags=["provider:cerebras"])
def _generate_cerebras(
    prompt: str,
    api_key: Optional[str],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    """Generate using Cerebras Cloud (native SDK)."""
    key = api_key or os.getenv("CEREBRAS_API_KEY")
    if not key:
        raise ValueError("CEREBRAS_API_KEY required")

    try:
        from cerebras.cloud.sdk import Cerebras
    except ImportError:
        raise ImportError("Install cerebras-cloud-sdk: uv add cerebras-cloud-sdk")

    client = Cerebras(api_key=key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=os.getenv("CEREBRAS_MODEL", "llama3.1-8b"),
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(
            f"Cerebras returned empty response (model={os.getenv('CEREBRAS_MODEL', 'llama3.1-8b')})"
        )
    return content.strip()
