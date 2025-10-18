def test_import_api_app():
    from football_rag.api.app import app  # type: ignore

    assert app is not None


def test_placeholder():
    assert True
