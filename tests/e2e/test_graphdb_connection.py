def test_graphdb_library(graphdb_triple_store, test_repository_names):
    graphdb = graphdb_triple_store
    available_repositories = set(graphdb.list_repositories())
    for test_repository_name in test_repository_names:
        if test_repository_name in available_repositories:
            graphdb.delete_repository(repository_name=test_repository_name)

    for test_repository_name in test_repository_names:
        graphdb.create_repository(repository_name=test_repository_name)

    available_repositories = set(graphdb.list_repositories())
    for test_repository_name in test_repository_names:
        assert test_repository_name in available_repositories

    for test_repository_name in test_repository_names:
        graphdb.delete_repository(repository_name=test_repository_name)

    available_repositories = set(graphdb.list_repositories())
    for test_repository_name in test_repository_names:
        assert test_repository_name not in available_repositories


def test_fuseki_triple_store_get_sparql_endpoint(graphdb_triple_store, tmp_repository_name, sparql_query_triples,
                                                 rdf_file_path):
    if tmp_repository_name not in graphdb_triple_store.list_repositories():
        graphdb_triple_store.create_repository(repository_name=tmp_repository_name)
    assert rdf_file_path.exists()

    sparql_endpoint = graphdb_triple_store.get_sparql_triple_store_endpoint(
        repository_name=tmp_repository_name)
    assert sparql_endpoint is not None
    df_query_result = sparql_endpoint.with_query(sparql_query=sparql_query_triples).fetch_tabular()
    assert df_query_result is not None
    current_number_of_triples = len(df_query_result)
    graphdb_triple_store.add_file_to_repository(rdf_file_path,
                                                repository_name=tmp_repository_name)
    df_query_result = sparql_endpoint.with_query(sparql_query=sparql_query_triples).fetch_tabular()
    assert df_query_result is not None
    assert len(df_query_result) > current_number_of_triples

    graphdb_triple_store.delete_repository(repository_name=tmp_repository_name)

    assert tmp_repository_name not in graphdb_triple_store.list_repositories()
