import json

from ted_data_eu.services.data_load_service import load_documents_to_storage


def test_elastic_storage_service(elastic_storage, document_file_path):
    assert document_file_path.exists()
    test_doc = json.loads(document_file_path.read_text(encoding='utf-8'))
    result = load_documents_to_storage([test_doc, test_doc])
    assert result['errors'] is False
    for item in result['items']:
        assert item['create']['status'] == 201


def test_elastic_storage(elastic_storage, document_file_path, elastic_query):
    assert document_file_path.exists()
    test_doc = document_file_path.read_text()
    response = elastic_storage.add_document(test_doc.encode('utf-8'))
    assert response.status_code == 201

    response = elastic_storage.query(elastic_query)
    assert response.status_code == 200

    response = elastic_storage.clear()
    assert response.status_code == 200
