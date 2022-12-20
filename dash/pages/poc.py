import json
from datetime import date, datetime
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback, dash_table
from pymongo import MongoClient
from ted_sws import config
import plotly.express as px
import pandas as pd

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
    # fig.update_layout(paper_bgcolor="lightgray")

    return fig


def resolve_q15(awarded_notes: int = None, last_state: int = None):
    query_result = data['q15']

    fig = go.Figure(go.Indicator(mode="number" if not last_state else "number+delta",
                                 value=awarded_notes if awarded_notes else query_result[0]['Total_Awardet_Lots'],
                                 title={"text": "Total Awarded Lots"},
                                 delta={'position': "top", 'reference': last_state},
                                 domain={'x': [0, 1], 'y': [0, 1]}))
    # fig.update_layout(paper_bgcolor="lightgray")

    return fig


@callback(
    Output('q15_graph', 'figure'),
    State('q15_graph', 'figure'),
    State('q15_daterange', 'start_date'),
    State('q15_daterange', 'end_date'),
    Input('q15_button', 'n_clicks'),
    prevent_initial_call=True,
)
def q15_callback(figure: dict, start_date: str, end_date: str, n_clicks: int):
    from ted_sws.data_manager.adapters.triple_store import FusekiAdapter
    fuseki_adapter = FusekiAdapter()
    fuseki_endpoint = fuseki_adapter.get_sparql_triple_store_endpoint('ted_data_dataset')

    query = Path('pages/q15.rq').read_text(encoding="utf-8")
    query = query.replace("(?ContractConclusionDate > '2000-01-01'", f"(?ContractConclusionDate > '{start_date}'")
    query = query.replace("?ContractConclusionDate < '2030-12-31'^^xsd:date",
                          f"?ContractConclusionDate < '{end_date}'^^xsd:date")

    result = fuseki_endpoint.with_query(query).fetch_tabular()['Total_Awardet_Lots'][0]
    new_value = result if result else 0
    last_value = figure['data'][0]['value']
    return resolve_q15(new_value, last_value)


@callback(
    Output("q2_graph", "figure"),
    Input("g2_dropdown", "value")
)
def generate_chart(value):
    # winner_country = [elem['Winner_Country'] for elem in data['q2']]
    # Lots_using_EU_Funds = [elem['Lots_using_EU_Funds'] for elem in data['q2']]

    dicts = dict(
        zip([elem['Winner_Country'] for elem in data['q2']], [elem['Lots_using_EU_Funds'] for elem in data['q2']]))

    if value:
        for elem in value:
            del dicts[elem]

    fig = go.Figure(data=[go.Pie(labels=list(dicts.keys()), values=list(dicts.values()))])
    # fig = px.pie(df, values='Lots_using_EU_Funds', names='Winner_Country', hole=.3)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    # fig.update_layout(paper_bgcolor="lightgray")
    return fig


def resolve_q3():
    country = [elem['Country'].split("/")[-1] for elem in data['q3']]
    nr_of_winners = [elem['Nr_of_winners'] for elem in data['q3']]
    total_value = [elem['TotalProcurementValue'] for elem in data['q3']]
    money_value = [elem['CurrencyID'].split("/")[-1] for elem in data['q3']]
    df = pd.DataFrame()
    df['Country'] = country
    df['nr_of_winners'] = nr_of_winners
    df['total_value'] = total_value
    df['money_value'] = money_value
    return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns])
    # return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], id='tbl')


layout = html.Div(children=[

    html.Center(children=[
        html.H1(children='POC of queries'),
        html.Br(),
        html.Div(children=[

            html.Div(children=[
                dcc.Graph(figure=resolve_q14()),
            ], style={'display': 'inline-block', 'vertical-align': 'top'}),
            html.Div(children=[
                dcc.Graph(id='q15_graph', figure=resolve_q15()),
                dcc.DatePickerRange(
                    id='q15_daterange',
                    min_date_allowed=date(1995, 8, 5),
                    max_date_allowed=date(2030, 9, 19),
                    # initial_visible_month=date(2022, 8, 5),
                    start_date=date(2020, 8, 5),
                    end_date=date(2022, 8, 25)
                ),
                html.Button('Submit', id='q15_button', n_clicks=0),

            ], style={'display': 'inline-block', "margin-left": "15px"})

        ], style={"border": "2px black solid"}),

        html.Br(),
        html.Div(children=[
            html.H1("Lots using EU Funds per winner country"),
            dcc.Graph(id="q2_graph", style={"height": "600px", "width": "100%"}),
            html.Br(),
            dcc.Dropdown([elem['Winner_Country'] for elem in data['q2']], multi=True, id="g2_dropdown",
                         style={"height": "50%", "width": "50%"})
        ], style={"border": "2px black solid"}),
        html.Br(),
        html.Div(children=[
            html.H1("Total value of winners per country"),
            resolve_q3()
        ], style={"border": "2px black solid"}),
    ])

], style={'display': "flex", "align-items": "center", "justify-content": "center"})
# "justify": "center", "align": "center", "className": "h-50"
# style={'margin-bottom': "-200", 'margin-right': "-300", 'margin-left': "-300"}
