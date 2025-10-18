def test_import_schemas():
    from football_rag.core.schemas import Answer, QueryRequest  # type: ignore

    assert QueryRequest and Answer


def test_query_request_bounds():
    from football_rag.core.schemas import QueryRequest  # type: ignore

    assert QueryRequest(question="valid").question == "valid"
