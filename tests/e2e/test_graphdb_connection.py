from ted_data_eu.adapters.triple_store import GraphDBAdapter


def test_graphdb_library(test_repository_names):
    graphdb = GraphDBAdapter()
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

