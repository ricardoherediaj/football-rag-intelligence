# Football RAG Intelligence - Architecture Decisions

**Purpose**: This file contains architectural decisions that don't change frequently. Reference this when understanding system design, but don't reload these decisions into context repeatedly.

**Last Updated**: 2026-02-13

---

## System Architecture Overview

**Vision**: Closed-loop sports intelligence platform that ingests match data, processes it via rigorous ETL, and serves tactical insights through a Hybrid RAG (SQL + Vector) agent.

**Core Philosophy**:
- **Zero-Cost Ingress**: Leverage local infrastructure (Docker/MinIO) for heavy lifting
- **Serverless Intelligence**: Leverage Modal/MotherDuck for on-demand inference
- **Data Integrity**: Strict schemas (Pydantic), idempotent pipelines, Medallion Architecture

---

## Technology Stack Rationale

### Storage Layer
**Local Development**:
- **MinIO** (S3-compatible): Local object storage for raw scraped data
  - Why: Free, Docker-native, S3 API compatibility for cloud migration
  - macOS Consideration: MUST use Docker named volumes (not bind mounts) due to VirtioFS latency
- **DuckDB**: Local analytical database
  - Why: Embedded, columnar, zero-ops, excellent for development

**Production/Cloud**:
- **MotherDuck**: Serverless DuckDB in the cloud
  - Why: Zero infrastructure, pay-per-query, DuckDB compatibility
  - Migration path: Local DuckDB → MotherDuck sync

### Processing Layer
- **Dagster**: Asset-based orchestration
  - Why: Asset lineage, declarative pipelines, better than Airflow for data assets
- **dbt Core (dbt-duckdb)**: SQL transformations
  - Why: Version-controlled SQL, testing framework, documentation generation
  - Medallion Architecture: Bronze (raw) → Silver (cleaned) → Gold (aggregated)

### Ingestion Layer
- **Playwright**: Web scraping with browser automation
  - Why: Handles JavaScript-heavy sites (FotMob), reliable, well-maintained

### Inference Layer
- **Modal**: Serverless GPU compute
  - Why: Pay-per-second, no infrastructure, GPU access for Llama 3 / vLLM
- **Opik**: LLM observability
  - Why: Track prompt performance, token usage, evaluation metrics

### Application Layer
- **Gradio** (MVP) → **React** (Future)
  - Why: Gradio for rapid prototyping, React for production UX

---

## Data Architecture

### Medallion Architecture

**Bronze Layer** (Raw Data):
- Direct scraper output stored in MinIO
- Minimal transformation (JSON → Parquet)
- Preserves original structure for reprocessing

**Silver Layer** (Cleaned Data):
- Schema enforcement via Pydantic models
- Data quality tests (dbt tests)
- Coordinate validation (x: 0-100, y: 0-100 for football pitch)
- Event type normalization

**Gold Layer** (Analytics-Ready):
- Aggregated metrics (player stats, match summaries)
- Denormalized for query performance
- Pre-computed features for RAG retrieval

### DuckDB → MotherDuck Sync Strategy
- Development: DuckDB local file (`data/football.duckdb`)
- Production: MotherDuck cloud instance
- Sync mechanism: dbt runs can target either backend via connection profiles

---

## RAG Architecture

### Hybrid RAG Design
**SQL Retrieval**:
- Structured queries for statistics (goals, assists, xG)
- Temporal queries (match timelines, season progression)

**Vector Retrieval**:
- Embeddings of match events, tactical patterns
- Semantic search for "similar plays" or "defensive breakdowns"

**Router Logic**:
- Classify query intent (statistical vs semantic)
- Route to appropriate retrieval backend
- Combine results for complex queries

### Embedding Strategy
- **Model**: TBD (Llama 3 embeddings via Modal or Sentence Transformers)
- **Storage**: DuckDB with vector extension OR separate vector DB (Qdrant/Chroma)
- **Granularity**: Event-level embeddings + match-level summaries

---

## Infrastructure Decisions

### Docker Strategy
**macOS Gotcha**:
- Bind mounts (`./data:/data`) cause MinIO crashes due to VirtioFS latency
- **SOLUTION**: Always use Docker named volumes for I/O-heavy services
- Example: `minio_data:/data` instead of `./data_lake:/data`

**Development Environment**:
```bash
docker-compose -f ops/docker-compose.yml up -d  # MinIO, Dagster UI (future)
```

### Python Environment
- **uv**: Dependency management (faster than pip, better than Poetry for our use case)
- **Python 3.10+**: Required for modern typing features
- **Virtual environments**: Managed by uv, isolated per project

---

## Deployment Strategy (Future)

**Current State**: Local development only

**Planned Path**:
1. **Phase 1** (Current): Local DuckDB + MinIO + Dagster
2. **Phase 2**: Migrate to MotherDuck + Modal inference
3. **Phase 3**: Cloud storage (S3/GCS) replaces MinIO
4. **Phase 4**: Production orchestration (Dagster Cloud or self-hosted)

---

## Anti-Patterns (Don't Do This)

❌ **Don't use bind mounts on macOS for MinIO** → Use named volumes
❌ **Don't hardcode file paths** → Use `pathlib.Path` and environment variables
❌ **Don't skip Pydantic validation** → All external data MUST pass schema validation
❌ **Don't write SQL in Python strings** → Use dbt models for transformations
❌ **Don't skip dbt tests** → Every Silver/Gold model needs row count + uniqueness tests
❌ **Don't abstract prematurely** → Build for current needs, refactor when patterns emerge
❌ **Don't duplicate Bronze data** → Raw data is immutable, reprocess if needed

---

## References
- Medallion Architecture: Standard data lake pattern (Bronze/Silver/Gold)
- DuckDB Docs: https://duckdb.org/docs/
- dbt Best Practices: https://docs.getdbt.com/best-practices
- Modal Docs: https://modal.com/docs
