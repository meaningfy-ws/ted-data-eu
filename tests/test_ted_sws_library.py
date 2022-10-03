from pymongo import MongoClient
from ted_sws import config
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.data_manager.adapters.triple_store import AllegroGraphTripleStore

TDA_REPOSITORY_NAME = "tda_repository"
REPO_MIME_TYPE = 'ttl'


def test_ted_sws_library():
    mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
    assert mongodb_client
    notice_repository = NoticeRepository(mongodb_client=mongodb_client)
    assert notice_repository
    notice_iter = notice_repository.list()

    agraph_ts = AllegroGraphTripleStore(host=config.ALLEGRO_HOST,
                                        user=config.AGRAPH_SUPER_USER,
                                        password=config.AGRAPH_SUPER_PASSWORD,
                                        default_repository=TDA_REPOSITORY_NAME)
    assert agraph_ts
    agraph_repositories = agraph_ts.list_repositories()
    assert agraph_repositories
    assert TDA_REPOSITORY_NAME in agraph_repositories

    notices_distilled_rdf_manifestation = {}
    for notice in notice_iter:
        if notice.distilled_rdf_manifestation:
            # TODO: check if notice already exist in agraph
            notices_distilled_rdf_manifestation[notice.ted_id] = notice.distilled_rdf_manifestation.object_data
