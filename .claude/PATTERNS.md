# Football RAG Intelligence - Coding Patterns

**Purpose**: Reference for coding standards and patterns. Claude already knows Python/SQL best practices—this file documents project-specific patterns and deviations from defaults.

**Last Updated**: 2026-02-13

---

## Python Style Guide

### Core Principles
- **Type hints mandatory** for all public functions
- **Pathlib over os.path** (always)
- **F-strings over .format()** (always)
- **Logging over print()** (use structlog or standard logging)

### Complexity Limits (Hard Limits)
| Element | Limit | Rationale |
|---------|-------|-----------|
| Function length | 20 lines | Forces single responsibility |
| File length | 300 lines | Prevents god objects |
| Nesting depth | 3 levels | Use guard clauses / early returns |
| Function arguments | 4 parameters | Use Pydantic models for more |

### Example: Guard Clauses Over Nesting
```python
# ❌ Bad (nested)
def process_event(event: dict) -> Optional[Event]:
    if event.get("type"):
        if event["type"] in VALID_TYPES:
            if event.get("coordinates"):
                return Event(**event)
    return None

# ✅ Good (guard clauses)
def process_event(event: dict) -> Optional[Event]:
    if not event.get("type"):
        return None
    if event["type"] not in VALID_TYPES:
        return None
    if not event.get("coordinates"):
        return None
    return Event(**event)
```

---

## Pydantic Model Patterns

### Schema Validation for All External Data
```python
from pydantic import BaseModel, Field, validator

class MatchEvent(BaseModel):
    """Match event with coordinate validation."""
    event_type: str
    x: float = Field(..., ge=0, le=100)  # Pitch coordinates 0-100
    y: float = Field(..., ge=0, le=100)
    timestamp: int = Field(..., ge=0)    # Seconds from kickoff

    @validator("event_type")
    def validate_event_type(cls, v):
        if v not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event type: {v}")
        return v
```

### Nested Models for Complex Structures
```python
class Player(BaseModel):
    id: int
    name: str
    position: str

class MatchLineup(BaseModel):
    home_team: list[Player]
    away_team: list[Player]

    @validator("home_team", "away_team")
    def validate_team_size(cls, v):
        if len(v) != 11:
            raise ValueError("Team must have exactly 11 players")
        return v
```

---

## File Organization Patterns

### Project Structure
```
src/football_rag/
├── data/              # Scrapers + Pydantic schemas
│   ├── scrapers/      # Playwright-based scrapers
│   └── schemas/       # Pydantic models
├── engine/            # RAG logic (Router, Vector Search)
├── utils/             # Shared helpers (logging, config)
└── api/               # FastAPI/Modal entrypoints (future)

dbt_project/
├── models/
│   ├── bronze/        # Raw data (minimal transformation)
│   ├── silver/        # Cleaned + validated
│   └── gold/          # Aggregated analytics
└── tests/             # dbt data quality tests

tests/                 # pytest unit/integration tests
├── unit/              # Pure function tests
└── integration/       # Full pipeline tests
```

### When to Create New Files
- **New file**: When adding a distinct capability (new scraper, new model type)
- **Extend existing**: When adding variations of existing functionality
- **Refactor**: When file exceeds 300 lines OR has >3 unrelated concepts

---

## dbt Model Patterns

### Naming Convention
```
bronze_<source>_<entity>.sql     # Example: bronze_fotmob_matches.sql
silver_<entity>.sql              # Example: silver_events.sql
gold_<metric>_<aggregation>.sql  # Example: gold_player_stats.sql
```

### Every Model Needs Tests
```yaml
# models/silver/silver_events.yml
version: 2

models:
  - name: silver_events
    description: "Cleaned match events with validated coordinates"
    columns:
      - name: event_id
        tests:
          - unique
          - not_null
      - name: x
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100
      - name: y
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100
```

### SQL Style (dbt Models)
```sql
-- ✅ Good: CTEs with clear naming, window functions for aggregations
with events_with_sequences as (
    select
        event_id,
        event_type,
        lag(event_type) over (partition by match_id order by timestamp) as prev_event,
        lead(event_type) over (partition by match_id order by timestamp) as next_event
    from {{ ref('silver_events') }}
),

pass_sequences as (
    select *
    from events_with_sequences
    where event_type = 'pass'
        and prev_event is not null
)

select * from pass_sequences
```

---

## Dagster Asset Patterns

### Asset Definition Example
```python
from dagster import asset, AssetExecutionContext
from pathlib import Path

@asset(
    description="Scrape FotMob match data for a specific match_id",
    group_name="scraping",
)
def bronze_fotmob_match(context: AssetExecutionContext, match_id: int) -> Path:
    """Scrape and store raw match data to MinIO."""
    scraper = FotMobScraper()
    data = scraper.fetch_match(match_id)

    # Store to MinIO (S3-compatible)
    output_path = Path(f"s3://bronze/fotmob/matches/{match_id}.json")
    write_json(output_path, data)

    context.log.info(f"Scraped match {match_id}: {len(data['events'])} events")
    return output_path
```

---

## Error Handling Patterns

### Don't Catch Everything
```python
# ❌ Bad: Swallows all errors
try:
    result = risky_operation()
except Exception:
    return None

# ✅ Good: Catch specific errors, let others bubble
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise
except KeyError as e:
    logger.warning(f"Missing key {e}, using default")
    result = default_value
```

### Only Handle Errors You Can Fix
- **Validation errors**: Catch, log, skip record (don't crash pipeline)
- **Network errors**: Retry with backoff, then fail loudly
- **File not found**: Check existence first (EAFP is Pythonic, but not for files)
- **Unexpected errors**: Let them crash (fail fast)

---

## Testing Patterns

### Test Structure (pytest)
```python
# tests/unit/test_event_parser.py
import pytest
from football_rag.data.schemas import MatchEvent

def test_event_parser_valid_coordinates():
    """Valid coordinates should pass validation."""
    event = MatchEvent(
        event_type="pass",
        x=50.0,
        y=30.5,
        timestamp=120
    )
    assert event.x == 50.0

def test_event_parser_invalid_x_coordinate():
    """X coordinate > 100 should raise ValidationError."""
    with pytest.raises(ValueError, match="x"):
        MatchEvent(event_type="pass", x=150.0, y=30.0, timestamp=120)

@pytest.fixture
def sample_match_data():
    """Reusable test data."""
    return {
        "match_id": 12345,
        "events": [
            {"type": "pass", "x": 50, "y": 50, "timestamp": 0}
        ]
    }
```

### Test Coverage Expectations
- **Unit tests**: All Pydantic models, parsers, transformations
- **Integration tests**: Full scraper → Bronze → Silver pipeline
- **dbt tests**: Row counts, uniqueness, range validation
- **No tests needed**: Simple getters, trivial property access

---

## Git Commit Patterns

### Conventional Commits (Strict)
```
<type>(<scope>): <description>

Types: feat, fix, chore, refactor, docs, test
Scopes: scraping, pipeline, dbt, dagster, rag, api

Examples:
feat(scraping): add FotMob shot map scraper
fix(dbt): correct silver_events coordinate validation
chore(deps): update uv.lock after adding httpx
refactor(pipeline): extract scraper retry logic to utils
docs(readme): add MotherDuck migration instructions
chore: add dbt project structure and consolidate legacy docs
```

**Preferred Style**:
- Keep description concise but complete (not cryptic)
- Use `chore:` without scope for multi-domain changes (deps + structure + cleanup)
- Use lowercase for all types and scopes
- Describe WHAT changed, not WHY (details go in commit body if needed)

### Co-Authorship (When Using Claude)
```bash
git commit -m "$(cat <<'EOF'
feat(pipeline): add full-season scraping with DuckDB Medallion pipeline

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Logging Patterns

### Use structlog for Structured Logging
```python
import structlog

logger = structlog.get_logger()

# ✅ Good: Structured fields
logger.info(
    "match_scraped",
    match_id=12345,
    events_count=150,
    duration_ms=1234
)

# ❌ Bad: String formatting loses queryability
logger.info(f"Scraped match 12345 with 150 events in 1234ms")
```

---

## References
- Python Type Hints: PEP 484, PEP 526
- Pydantic Docs: https://docs.pydantic.dev/
- pytest Best Practices: https://docs.pytest.org/en/stable/goodpractices.html
- Conventional Commits: https://www.conventionalcommits.org/
