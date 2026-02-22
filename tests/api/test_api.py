import pytest


@pytest.mark.skip(reason="API module not built yet — placeholder for Phase 4")
def test_import_api_app():
    from football_rag.app.app import app  # type: ignore

    assert app is not None


def test_placeholder():
    assert True
