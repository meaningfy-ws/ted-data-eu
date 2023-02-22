from typing import Dict, List

from ted_data_eu.adapters.storage import ElasticStorage
from ted_data_eu.adapters.storage_abc import DocumentStorageABC
from ted_data_eu import config


def load_documents_to_storage(documents: List[Dict],
                              storage: DocumentStorageABC = None) -> Dict:
    """
        Loads data in document format to a storage.

    :param documents: List of dict to be stored
    :param storage: Document storage where Data will be loaded. If not specified, default (Elastic Storage) will be used
    :return: dict with Elastic API Response
    """

    if not storage:
        storage = ElasticStorage(elastic_index=config.ELASTIC_DEFAULT_INDEX)

    return storage.add_documents(documents=documents)
