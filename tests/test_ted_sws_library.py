from pymongo import MongoClient
from ted_sws import config
from ted_sws.data_manager.adapters.notice_repository import NoticeRepository
from ted_sws.data_manager.adapters.triple_store import AllegroGraphTripleStore

TDA_REPOSITORY_NAME = "tda_repository"


def test_ted_sws_library():
    mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
    notice_repository = NoticeRepository(mongodb_client=mongodb_client)
    notice_iter = notice_repository.list()
    # notices_distilled_rdf_manifestation = {notice.ted_id: notice.distilled_rdf_manifestation.object_data
    #                                       for notice in notice_list if notice.distilled_rdf_manifestation}

    nr_of_notices = 0
    notices_distilled_rdf_manifestation = {}
    for notice in notice_iter:
        if notice.distilled_rdf_manifestation:
            notices_distilled_rdf_manifestation[notice.ted_id] = notice.distilled_rdf_manifestation.object_data
        nr_of_notices += 1
    notices_distilled_rdf_manifestation_len = len(notices_distilled_rdf_manifestation)

    print('')
    print(f'Number of notices: {nr_of_notices}')
    print(f'Number of distilled_rdf_manifestation: {notices_distilled_rdf_manifestation_len}')

    assert notices_distilled_rdf_manifestation_len > 0, "There are no notices_distilled_rdf_manifestation"

    agraph_ts = AllegroGraphTripleStore(host=config.ALLEGRO_HOST,
                                        user=config.AGRAPH_SUPER_USER,
                                        password=config.AGRAPH_SUPER_PASSWORD,
                                        default_repository=TDA_REPOSITORY_NAME
                                        )

    agraph_repositories = agraph_ts.list_repositories()

    if TDA_REPOSITORY_NAME not in agraph_repositories:
        agraph_ts.create_repository(repository_name=TDA_REPOSITORY_NAME)

    print("Start load rdf content")
    for notice_id, rdf_content in notices_distilled_rdf_manifestation.items():
        print(f"Start load rdf content for notice_id={notice_id}")
        agraph_ts.add_data_to_repository(file_content=rdf_content, mime_type="ttl")
        print(f"Finish load rdf content for notice_id={notice_id}")
    print("Load rdf content done")
