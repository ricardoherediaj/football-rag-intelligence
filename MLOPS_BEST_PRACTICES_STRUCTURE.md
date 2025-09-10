# Football RAG Intelligence - MLOps/LLMOps Best Practices Structure

## 🎯 Philosophy: **Educational Best Practices**
- ✅ Real MLOps patterns (not toys)
- ✅ Clean, understandable code
- ✅ Industry-standard tools (Prefect, MLflow, Opik)
- ✅ Proper separation of concerns
- ❌ Over-engineering
- ❌ Unnecessary abstractions

## 📁 Clean MLOps Structure

```
football-rag-intelligence/
├── src/football_rag/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Pydantic Settings (best practice)
│   │   └── logging_config.py        # Structured logging setup
│   ├── data/
│   │   ├── __init__.py
│   │   ├── schemas.py               # Pydantic models (data contracts)
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Abstract scraper pattern
│   │   │   ├── whoscored.py         # Concrete implementation
│   │   │   └── fotmob.py            # Concrete implementation
│   │   ├── preprocessing.py         # Data transformation
│   │   └── storage.py               # Data persistence layer
│   ├── flows/                       # Prefect workflows (orchestration)
│   │   ├── __init__.py
│   │   ├── data_ingestion.py        # ETL flow
│   │   ├── model_training.py        # Embedding/model updates
│   │   └── inference.py             # RAG pipeline flow
│   ├── models/
│   │   ├── __init__.py
│   │   ├── embeddings.py            # Embedding model wrapper
│   │   ├── llm.py                   # LLM wrapper (Llama/OpenAI)
│   │   └── rag_pipeline.py          # RAG orchestration
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py               # Custom evaluation metrics
│   │   ├── evaluators.py            # LLM-as-judge implementations
│   │   └── experiments.py           # MLflow experiment management
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── opik_tracer.py           # LLM call tracing
│   │   ├── mlflow_logger.py         # Experiment logging
│   │   └── alerts.py                # Quality alerts
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── endpoints.py             # API routes
│   │   └── dependencies.py          # Dependency injection
│   └── utils/
│       ├── __init__.py
│       ├── database.py              # DB connections
│       └── visualization.py         # Chart generation
├── flows/                           # Prefect deployment files
│   ├── deployments.py               # Flow deployments
│   └── schedules.py                 # Scheduling configuration
├── config/
│   ├── settings.yaml                # Environment configuration
│   ├── model_config.yaml           # Model hyperparameters
│   └── evaluation_config.yaml      # Evaluation settings
├── scripts/
│   ├── setup_infrastructure.py     # Initialize services
│   ├── run_evaluation.py           # Manual evaluation runs
│   └── deploy.py                    # Deployment utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                        # End-to-end tests
├── docker/
│   ├── Dockerfile                  # Application container
│   ├── docker-compose.yml          # Development services
│   └── docker-compose.prod.yml     # Production services
├── .github/
│   └── workflows/
│       ├── test.yml                # CI pipeline
│       ├── deploy.yml              # CD pipeline
│       └── quality.yml             # Code quality checks
├── requirements/
│   ├── base.txt                    # Core dependencies
│   ├── dev.txt                     # Development tools
│   └── prod.txt                    # Production extras
├── pyproject.toml                  # Modern Python packaging
├── prefect.yaml                    # Prefect configuration
├── mlflow.yaml                     # MLflow configuration
└── README.md                       # Clear documentation
```

## 🔧 Best Practices Implementation

### 1. **Configuration Management (Pydantic Settings)**
```python
# src/football_rag/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    minio_endpoint: str = "localhost:9000"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    # Models  
    embedding_model: str = "all-mpnet-base-v2"
    llm_model: str = "llama3.2:1b"
    
    # MLOps
    mlflow_tracking_uri: str = "http://localhost:5000"
    opik_api_key: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 2. **Orchestration with Prefect (Clean Flows)**
```python
# src/football_rag/flows/data_ingestion.py
from prefect import flow, task
from prefect.logging import get_run_logger

@task(retries=3, retry_delay_seconds=60)
async def scrape_match_data(match_id: str) -> dict:
    logger = get_run_logger()
    logger.info(f"Scraping match {match_id}")
    # Scraping logic
    return match_data

@task
async def process_and_store(match_data: dict) -> str:
    # Processing logic
    return storage_path

@flow(name="football-data-ingestion")
async def ingest_match_data(match_ids: list[str]):
    """Main data ingestion flow with proper error handling."""
    results = []
    for match_id in match_ids:
        match_data = await scrape_match_data(match_id)
        storage_path = await process_and_store(match_data)
        results.append(storage_path)
    return results
```

### 3. **Experiment Tracking (MLflow)**
```python
# src/football_rag/evaluation/experiments.py
import mlflow
from mlflow.models import infer_signature

class ExperimentManager:
    def __init__(self):
        mlflow.set_tracking_uri("http://localhost:5000")
        
    def log_embedding_experiment(self, model_name: str, metrics: dict):
        with mlflow.start_run(experiment_id="embedding-experiments"):
            mlflow.log_param("model_name", model_name)
            mlflow.log_metrics(metrics)
            mlflow.log_model(model, "embedding_model")
```

### 4. **LLM Monitoring (Opik)**
```python
# src/football_rag/monitoring/opik_tracer.py
from opik import track

@track
def rag_query(question: str, context: list[str]) -> str:
    """Tracked RAG query for monitoring."""
    response = llm.generate(question, context)
    return response

# Automatic tracking of:
# - Input/output
# - Latency
# - Token usage  
# - Quality scores
```

### 5. **Data Contracts (Pydantic Schemas)**
```python
# src/football_rag/data/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime

class MatchEvent(BaseModel):
    match_id: str = Field(..., description="Unique match identifier")
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="When event occurred")
    player_id: str | None = Field(None, description="Player involved")
    
    class Config:
        json_schema_extra = {
            "example": {
                "match_id": "123456",
                "event_type": "shot",
                "timestamp": "2024-01-01T15:30:00Z",
                "player_id": "player_123"
            }
        }
```

### 6. **Evaluation Framework**
```python
# src/football_rag/evaluation/evaluators.py
from mlflow.evaluate import make_eval_function

@make_eval_function
def faithfulness_evaluator(prediction: str, context: str) -> dict:
    """LLM-as-judge for faithfulness evaluation."""
    score = llm_judge.evaluate_faithfulness(prediction, context)
    return {"faithfulness_score": score}

# Automatic evaluation on each model update
```

## 🚀 Development Workflow

### Phase 1: Foundation (Week 1-2)
1. **Setup infrastructure**: Docker Compose with all services
2. **Basic data pipeline**: Scrapers → Storage → Processing
3. **Simple RAG**: Embeddings → Retrieval → Generation
4. **Monitoring setup**: MLflow + Opik integration

### Phase 2: Best Practices (Week 3-4)  
1. **Prefect flows**: Convert scripts to orchestrated workflows
2. **Evaluation framework**: Automated quality assessment
3. **Experiment tracking**: A/B test prompts and models
4. **API development**: Production-ready FastAPI

### Phase 3: Production (Week 5-6)
1. **CI/CD pipeline**: GitHub Actions for quality gates
2. **Deployment**: HuggingFace Spaces with monitoring
3. **Performance optimization**: Caching, async, scaling
4. **Documentation**: Complete setup and usage guides

## 💡 Key Learning Outcomes

You'll learn:
- **Prefect**: Modern workflow orchestration
- **MLflow**: Experiment tracking and model registry
- **Opik**: LLM observability and monitoring  
- **Pydantic**: Data validation and settings management
- **FastAPI**: Production API development
- **Docker**: Containerization and service orchestration
- **Testing**: Unit, integration, and E2E testing
- **CI/CD**: Automated quality gates and deployment

This structure teaches you **real MLOps practices** without overwhelming complexity!