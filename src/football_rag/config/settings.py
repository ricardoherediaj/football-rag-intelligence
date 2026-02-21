"""Configuration settings for the application."""
import os
from dataclasses import dataclass

# Try to load .env manually if not loaded
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class ModelSettings:
    temperature: float = 0.3
    default_provider: str = "anthropic"


class Settings:
    duckdb_path: str = os.getenv("DUCKDB_PATH", "data/lakehouse.duckdb")
    models = ModelSettings()
    prompt_profile: str = "v3.5_balanced"

    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")


settings = Settings()