#!/bin/bash
# Wrapper launched by launchd to start dagster-daemon with env vars from .env
# launchd cannot source .env directly, so this script handles it.

PROJECT_DIR="/Users/ricardoheredia/football-rag-intelligence"

# Load env vars from .env (skip comments and empty lines)
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

export DAGSTER_HOME="$PROJECT_DIR/ops/dagster_home_local"

exec "$PROJECT_DIR/.venv/bin/dagster-daemon" run
