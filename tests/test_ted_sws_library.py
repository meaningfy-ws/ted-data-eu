from pymongo import MongoClient
from ted_sws import config
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.data_manager.adapters.triple_store import AllegroGraphTripleStore

TDA_REPOSITORY_NAME = "tda_repository"


def test_ted_sws_library():
    mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
    notice_repository = NoticeRepository(mongodb_client=mongodb_client)
    notices_distilled_rdf_manifestation = {notice.ted_id: notice.distilled_rdf_manifestation.object_data
                                           for notice in notice_repository.list() if notice.distilled_rdf_manifestation}

    #     Dima after this just load data in Agraph

    agraph_ts = AllegroGraphTripleStore(host=config.ALLEGRO_HOST,
                                        user=config.AGRAPH_SUPER_USER,
                                        password=config.AGRAPH_SUPER_PASSWORD,
                                        default_repository= TDA_REPOSITORY_NAME
                                        )

    agraph_repositories = agraph_ts.list_repositories()

    if TDA_REPOSITORY_NAME not in agraph_repositories:
        agraph_ts.create_repository(repository_name=TDA_REPOSITORY_NAME)

    for notice_id, rdf_content in notices_distilled_rdf_manifestation.items():
        print(f"Start load rdf content for notice_id={notice_id}")
        agraph_ts.add_data_to_repository(file_content=rdf_content, mime_type="ttl")
        print(f"Finish load rdf content for notice_id={notice_id}")
