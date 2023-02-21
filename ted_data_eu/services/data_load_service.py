import json
from typing import Dict, List

from ted_data_eu.adapters.storage import ElasticStorage
from ted_data_eu.adapters.storage_abc import DocumentStorageABC

ELASTIC_DEFAULT_INDEX = 'ted_data'


def load_documents_to_storage(documents: List[Dict],
                              storage: DocumentStorageABC = None) -> Dict:
    """
        Loads data in document format to a storage.

    :param documents: List of dict to be stored
    :param storage: Document storage where Data will be loaded. If not specified, default (Elastic Storage) will be used
    """

    if not storage:
        storage = ElasticStorage(index=ELASTIC_DEFAULT_INDEX)

    processed_documents = []
    for document in documents:
        processed_documents.append(json.dumps(document))

    response = storage.add_documents(documents=processed_documents)
    return json.loads(response.content)
