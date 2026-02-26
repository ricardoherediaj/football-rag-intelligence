"""Shared pytest configuration."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-edd",
        action="store_true",
        default=False,
        help="Run EDD tests that call the live LLM pipeline",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require Playwright / live network",
    )
    parser.addoption(
        "--run-local-data",
        action="store_true",
        default=False,
        help="Run tests that require lakehouse.duckdb or MinIO on disk",
    )


def pytest_collection_modifyitems(config, items):
    """Skip marker-gated tests unless the matching flag is passed."""
    skip_integration = pytest.mark.skip(reason="needs --run-integration flag")
    skip_local_data = pytest.mark.skip(reason="needs --run-local-data flag")
    skip_edd = pytest.mark.skip(reason="needs --run-edd flag")

    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(skip_integration)
        if "local_data" in item.keywords and not config.getoption("--run-local-data"):
            item.add_marker(skip_local_data)
        if "edd" in item.keywords and not config.getoption("--run-edd"):
            item.add_marker(skip_edd)
