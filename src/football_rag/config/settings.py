"""Clean configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    chroma_host: str = "localhost"
    chroma_port: int = 8000


class ModelSettings(BaseSettings):
    """Model configuration settings."""

    embedding_model: str = "all-mpnet-base-v2"
    llm_model: str = "llama3.2:1b"
    max_context_length: int = 4096
    temperature: float = 0.1


class MLOpsSettings(BaseSettings):
    """MLOps tools configuration."""

    mlflow_tracking_uri: str = "http://localhost:5001"
    opik_api_key: str = ""
    prefect_api_url: str = "http://localhost:4200/api"


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Database Settings
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Model Settings
    embedding_model: str = "all-mpnet-base-v2"
    llm_model: str = "qwen3:0.6b"
    max_context_length: int = 4096
    temperature: float = 0.1

    # MLOps Settings
    mlflow_tracking_uri: str = "http://localhost:5001"
    opik_api_key: str = ""

    # Application Settings
    debug: bool = False
    log_level: str = "INFO"

    # Prompt and runtime defaults
    prompt_profile: str = "profile_football_v1"
    llm_timeout_ms: int = 120000
    llm_retries: int = 2
    cache_ttl_s: int = 120
    default_top_k: int = 4

    @property
    def database(self) -> DatabaseSettings:
        return DatabaseSettings(
            minio_endpoint=self.minio_endpoint,
            minio_access_key=self.minio_access_key,
            minio_secret_key=self.minio_secret_key,
            chroma_host=self.chroma_host,
            chroma_port=self.chroma_port,
        )

    @property
    def models(self) -> ModelSettings:
        return ModelSettings(
            embedding_model=self.embedding_model,
            llm_model=self.llm_model,
            max_context_length=self.max_context_length,
            temperature=self.temperature,
        )

    @property
    def mlops(self) -> MLOpsSettings:
        return MLOpsSettings(
            mlflow_tracking_uri=self.mlflow_tracking_uri, opik_api_key=self.opik_api_key
        )


# Global settings instance
settings = Settings()
