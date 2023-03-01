import json

import pytest
from ted_data_eu.services.data_load_service import load_documents_to_storage


def test_elastic_storage_service(elastic_storage, document_file_path,elastic_query):
    elastic_storage.clear()
    assert elastic_storage.count() == 0
    assert document_file_path.exists()
    test_doc = json.loads(document_file_path.read_text(encoding='utf-8'))
    load_documents_to_storage([test_doc, test_doc], elastic_storage)
    assert elastic_storage.count() == 2
    documents = elastic_storage.query(elastic_query)
    assert len(documents) == 2
    assert documents[0] == test_doc
    assert documents[1] == test_doc
    elastic_storage.clear()
    assert elastic_storage.count() == 0


def test_elastic_storage(elastic_storage, document_file_path, elastic_query):
    assert document_file_path.exists()
    test_doc = json.loads(document_file_path.read_text())
    elastic_storage.clear()
    assert elastic_storage.count() == 0
    elastic_storage.add_document(test_doc)
    assert elastic_storage.count() == 1
    with pytest.raises(Exception):
        elastic_storage.query({"invalid_query":{}})
    documents = elastic_storage.query(elastic_query)
    assert len(documents) == 1
    assert documents[0] == test_doc
    elastic_storage.clear()
    assert elastic_storage.count() == 0

