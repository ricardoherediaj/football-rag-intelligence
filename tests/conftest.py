"""Shared pytest configuration."""


def pytest_addoption(parser):
    parser.addoption(
        "--run-edd",
        action="store_true",
        default=False,
        help="Run EDD tests that call the live LLM pipeline",
    )
