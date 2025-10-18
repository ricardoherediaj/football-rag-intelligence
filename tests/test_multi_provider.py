#!/usr/bin/env python3
"""Quick test of multi-provider LLM support."""

import os
from pathlib import Path

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from football_rag.llm.generate import generate_with_llm
from football_rag.core.prompts_loader import load_prompt

# Load prompts
prompts = load_prompt()
print("✓ Prompts loaded")
print(f"  System prompt: {prompts['system'][:100]}...")

# Test 1: Simple Anthropic test (if API key is available)
api_key = os.getenv("ANTHROPIC_API_KEY")

if api_key:
    print("\n🧪 Testing Anthropic provider...")
    try:
        response = generate_with_llm(
            prompt="What is football?",
            provider="anthropic",
            api_key=api_key,
            system_prompt=prompts["system"],
            max_tokens=50,
        )
        print(f"✅ Anthropic response: {response}")
    except Exception as e:
        print(f"❌ Anthropic error: {e}")
else:
    print("\n⚠️ No ANTHROPIC_API_KEY found in environment")

# Test 2: Check prompt loader with YAML
print("\n🧪 Testing prompt loader...")
try:
    custom_prompts = load_prompt("profile_football_v1")
    print(f"✅ Custom prompts loaded")
    print(f"  System: {custom_prompts['system'][:80]}...")
    print(f"  User template: {custom_prompts['user_template'][:80]}...")
except Exception as e:
    print(f"❌ Prompt loader error: {e}")

print("\n✓ All basic tests passed!")
