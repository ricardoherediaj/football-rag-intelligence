# Scripts Documentation

## Migration Script: `migrate_csv_to_minio.py`

Uploads existing WhoScored CSV data to MinIO as individual match JSON files.

### Usage:
```bash
uv run python scripts/migrate_csv_to_minio.py
```

### What it does:
- Reads `data/raw/eredivisie_2025_2026_whoscored.csv`
- Splits data by match
- Uploads each match as `whoscored/eredivisie/2025-2026/match_{id}.json` to MinIO
- Skips matches that already exist

---

## WhoScored Scraper

### Full Scrape (initial backfill):
```bash
uv run python -m football_rag.data.whoscored_scraper --mode full
```

### Incremental Scrape (only new matches):
```bash
uv run python -m football_rag.data.whoscored_scraper --mode incremental
```

### Custom league/season:
```bash
uv run python -m football_rag.data.whoscored_scraper --mode incremental --league eredivisie --season 2025-2026
```

### What it does:
- **Full mode**: Scrapes all finished matches from the season
- **Incremental mode**: Checks MinIO for already scraped matches, only scrapes new ones
- Saves backup CSV to `data/raw/`
- Uploads individual match JSON files to MinIO
- Automatically handles duplicate detection

---

## Fotmob Scraper

### Full Scrape (initial backfill):
```bash
uv run python -m football_rag.data.fotmob_scraper --mode full
```

### Incremental Scrape (only new matches):
```bash
uv run python -m football_rag.data.fotmob_scraper --mode incremental
```

### Custom league/season:
```bash
uv run python -m football_rag.data.fotmob_scraper --mode incremental --league eredivisie --season 2025-2026
```

### What it does:
- **Full mode**: Scrapes all finished matches from Eredivisie (54 matches)
- **Incremental mode**: Checks MinIO for already scraped matches, only scrapes new ones
- Saves backup JSON to `data/raw/`
- Uploads individual match JSON files to MinIO (`fotmob/eredivisie/2025-2026/match_{id}.json`)
- Extracts shot data with xG, player info, and match details

---

## Current Data Status

### WhoScored: ✅ Complete
- **53 matches** with event-level data
- Storage: `whoscored/eredivisie/2025-2026/match_{id}.json`
- Contains: All match events (passes, shots, tackles, etc.)

### Fotmob: ✅ Complete
- **54 matches** with shot data
- Storage: `fotmob/eredivisie/2025-2026/match_{id}.json`
- Contains: Shot details with xG, coordinates, player info

### Workflow

#### Initial Setup (one-time) - COMPLETED:
1. ✅ Migrated WhoScored CSV to MinIO: `uv run python scripts/migrate_csv_to_minio.py`
2. ✅ Scraped all Fotmob matches: `uv run python -m football_rag.data.fotmob_scraper --mode full`

#### Regular Updates (automated):
```bash
# Weekly after gameweek completion
uv run python -m football_rag.data.whoscored_scraper --mode incremental
uv run python -m football_rag.data.fotmob_scraper --mode incremental
```

This ensures you only scrape new matches and avoid re-scraping existing data.