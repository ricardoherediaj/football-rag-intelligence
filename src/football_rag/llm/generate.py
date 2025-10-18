"""Simple LLM generation function supporting multiple providers."""

from typing import Optional

from football_rag.core.logging import get_logger

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
        provider: 'ollama', 'anthropic', 'openai', or 'gemini'
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
        return _generate_anthropic(
            prompt, api_key, system_prompt, temperature, max_tokens
        )
    elif provider == "openai":
        return _generate_openai(prompt, api_key, system_prompt, temperature, max_tokens)
    elif provider == "gemini":
        return _generate_gemini(prompt, api_key, system_prompt, temperature, max_tokens)
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
        model="claude-3-5-haiku-20241022",
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt or "",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


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
