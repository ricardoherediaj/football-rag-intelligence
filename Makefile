# Football RAG Intelligence - Development Commands

.PHONY: help test-scrapers run-scrapers run-whoscored run-fotmob setup lint format

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Testing commands
test-scrapers:  ## Run scraper validation tests
	uv run python tests/test_scrapers.py

test:  ## Run all tests with pytest
	uv run pytest tests/ -v

# Scraper execution commands  
run-scrapers:  ## Run the main scrapers.py module
	uv run python -m football_rag.data.scrapers

run-whoscored:  ## Test WhoScored scraper with single match
	uv run python -c "from football_rag.data.scrapers import WhoScoredScraper; \
	scraper = WhoScoredScraper(headless=True); \
	urls = scraper.get_eredivisie_match_urls(); \
	print(f'Found {len(urls)} matches'); \
	df = scraper.scrape_single_match(urls[0]) if urls else None; \
	scraper.close(); \
	print(f'Scraped {len(df)} events' if df is not None else 'Scraping failed')"

run-fotmob:  ## Test Fotmob scraper with test match
	uv run python -c "from football_rag.data.scrapers import FotmobScraper; \
	scraper = FotmobScraper(); \
	df = scraper.scrape_shots(4825080); \
	print(f'Scraped {len(df)} shots' if df is not None else 'Scraping failed')"

# WhoScored scraper commands
scrape-whoscored:  ## Run WhoScored scraper for complete season
	uv run python -m football_rag.data.whoscored_scraper

# Development setup
setup:  ## Install dependencies and setup development environment
	uv pip install -e .
	docker-compose up -d

# Code quality
lint:  ## Run linter
	uv run ruff check

format:  ## Format code
	uv run ruff format

lint-fix:  ## Run linter with auto-fix
	uv run ruff check --fix

# Infrastructure
services-up:  ## Start Docker services (MLflow, MinIO, ChromaDB)
	docker-compose up -d

services-down:  ## Stop Docker services
	docker-compose down

services-logs:  ## Show Docker services logs
	docker-compose logs -f

# Application
run-api:  ## Run FastAPI + Gradio interface
	uv run python -m football_rag.api.app

run-api-dev:  ## Run with auto-reload for development
	uv run uvicorn football_rag.api.app:app --reload