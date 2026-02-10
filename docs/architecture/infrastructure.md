# 🏗️ Infrastructure Documentation

This document details the V2 "Data Lakehouse" architecture running on Docker.

## 🧱 Core Services

| Service | Container Name | Port | Credentials | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Dagster UI** | `football_orchestrator` | `3000` | N/A | Orchestration control plane. View pipelines, assets, and launch runs. |
| **Dagster Daemon** | `football_scheduler` | N/A | N/A | Background process for Schedules, Sensors, and Run Queue. |
| **MinIO** | `football_datalake` | `9001` (UI)<br>`9000` (API) | `admin` / `password123` | S3-compatible Object Storage for raw and processed data. |
| **Postgres** | `dagster_db` | `5432` | `postgres_user` / `postgres_password` | Metadata storage for Dagster (run history, event logs). |

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose

### Commands

**Start the Platform**
```bash
docker compose up --build -d
```
The `--build` flag is recommended to ensure the Ops image includes the latest `dagster.yaml` or python dependencies.

**Stop the Platform**
```bash
docker compose down
```

**View Logs**
```bash
docker logs -f football_orchestrator
docker logs -f football_scheduler
```

## 📂 Directory Structure

- `ops/`: Contains Dockerfiles and infrastructure configuration (`dagster.yaml`).
- `ops/dagster_home/`: Mounted as `$DAGSTER_HOME` inside containers.
- `orchestration/`: Python code for Dagster definitions (jobs, assets).
- `data_lake/`: Local folder mapped to MinIO storage bucket.
