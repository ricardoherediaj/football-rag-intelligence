FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/dagster/app

# Install Python dependencies
# We install dagster, webserver, postgres, and aws (for MinIO)
RUN pip install \
    dagster \
    dagster-webserver \
    dagster-postgres \
    dagster-aws \
    dagster-docker

# Set environment variables
ENV DAGSTER_HOME=/opt/dagster/dagster_home

# Create Dagster home directory
RUN mkdir -p $DAGSTER_HOME

# Copy dagster instance config
COPY dagster.yaml $DAGSTER_HOME/

# Copy workspace code
COPY workspace.yaml /opt/dagster/app/

# We will mount the user code in docker-compose, but we can copy a default stub
# COPY src /opt/dagster/app/src

WORKDIR /opt/dagster/app
