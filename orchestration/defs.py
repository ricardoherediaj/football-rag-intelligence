from dagster import Definitions, load_assets_from_modules
from orchestration.assets import dbt_assets, duckdb_assets, embeddings_assets, match_mapping_asset, scrapers
from orchestration.schedules import (
    eredivisie_scrape_schedule,
    post_scrape_transform_sensor,
    scrape_and_load_job,
    transform_job,
)

all_assets = load_assets_from_modules(
    [dbt_assets, duckdb_assets, embeddings_assets, match_mapping_asset, scrapers]
)

defs = Definitions(
    assets=all_assets,
    schedules=[eredivisie_scrape_schedule],
    sensors=[post_scrape_transform_sensor],
    jobs=[scrape_and_load_job, transform_job],
)
