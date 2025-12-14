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
class DatabaseSettings:
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", 8000))
    # Path for local persistence
    persist_directory: str = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")

@dataclass
class ModelSettings:
    temperature: float = 0.3
    default_provider: str = "anthropic"

class Settings:
    database = DatabaseSettings()
    models = ModelSettings()
    prompt_profile: str = "v3.5_balanced"
    
    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()