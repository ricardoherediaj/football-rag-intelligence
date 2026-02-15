from dagster import Definitions, load_assets_from_modules
from orchestration.assets import dbt_assets, duckdb_assets, embeddings_assets, match_mapping_asset, scrapers

# Load all assets from the modules
all_assets = load_assets_from_modules(
    [dbt_assets, duckdb_assets, embeddings_assets, match_mapping_asset, scrapers]
)

defs = Definitions(
    assets=all_assets,
)
