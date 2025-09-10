"""Clean configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    minio_access_key: str = Field(default="minioadmin", description="MinIO access key")
    minio_secret_key: str = Field(default="minioadmin", description="MinIO secret key")
    
    chroma_host: str = Field(default="localhost", description="Chroma host")
    chroma_port: int = Field(default=8000, description="Chroma port")
    

class ModelSettings(BaseSettings):
    """Model configuration settings."""
    
    embedding_model: str = Field(
        default="all-mpnet-base-v2", 
        description="Sentence transformer model for embeddings"
    )
    llm_model: str = Field(
        default="llama3.2:1b",
        description="LLM model name (Ollama format)"
    )
    max_context_length: int = Field(default=4096, description="Maximum context length")
    temperature: float = Field(default=0.1, description="LLM temperature")


class MLOpsSettings(BaseSettings):
    """MLOps tools configuration."""
    
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000", 
        description="MLflow tracking server URI"
    )
    opik_api_key: str = Field(default="", description="Opik API key for LLM monitoring")
    prefect_api_url: str = Field(
        default="http://localhost:4200/api", 
        description="Prefect API URL"
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    models: ModelSettings = ModelSettings()
    mlops: MLOpsSettings = MLOpsSettings()
    
    # Application settings
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()