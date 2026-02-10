FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libgbm1 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (The Python Package Manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /opt/dagster/app

# Set environment variables
ENV DAGSTER_HOME=/opt/dagster/dagster_home
# Ensure the virtual environment is used
ENV PATH="/opt/dagster/app/.venv/bin:$PATH"
# UV settings
ENV UV_COMPILE_BYTECODE=1 

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install dependencies
RUN uv sync --frozen --no-cache

# Install Playwright browsers (chromium)
# Note: We need to use valid pip/python from the venv
RUN uv run playwright install chromium --with-deps

# Create Dagster home directory
RUN mkdir -p $DAGSTER_HOME

# Copy dagster instance config
COPY ops/dagster.yaml $DAGSTER_HOME/

# Copy workspace code
COPY ops/workspace.yaml /opt/dagster/app/

# We will mount the user code in docker-compose
# COPY src /opt/dagster/app/src

WORKDIR /opt/dagster/app
