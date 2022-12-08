import dash
import plotly.graph_objects as go
from dash import html, dcc
from pymongo import MongoClient
from ted_sws import config

dash.register_page(__name__)


def get_data() -> dict:
    TED_DATA_MONGODB_DATABASE_NAME = 'ted_analytics'  # TODO: temporary while not put in config resolver

    mongodb_client = MongoClient(config.MONGO_DB_AUTH_URL)
    mongodb_database = mongodb_client[TED_DATA_MONGODB_DATABASE_NAME]
    mongodb_collections = mongodb_database.list_collection_names()
    if not mongodb_collections:
        return dict()

    queries_data: dict = {}
    for collection_name in mongodb_collections:
        collection = mongodb_database[collection_name]
        queries_data[collection_name] = list(collection.find({}))
    return queries_data


data: dict = get_data()


def resolve_q14():
    query_result = data['q14']

    fig = go.Figure(go.Indicator(mode="number", value=query_result[0]['Nr_of_SME'], title={"text": "Nr of SME"},
                                 delta={'position': "top", 'reference': 320}, domain={'x': [0, 1], 'y': [0, 1]}))
    fig.update_layout(paper_bgcolor="lightgray")

    return fig


layout = html.Div(children=[
    html.H1(children='POC of queries'),
    html.Br(),

    dcc.Graph(figure=resolve_q14())

])
