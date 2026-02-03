from dagster import Definitions, load_assets_from_modules
from orchestration.assets import duckdb_assets, scrapers

# Load all assets from the modules
all_assets = load_assets_from_modules([duckdb_assets, scrapers])

defs = Definitions(
    assets=all_assets,
)
