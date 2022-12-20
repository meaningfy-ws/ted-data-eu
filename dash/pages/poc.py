from datetime import date
from pathlib import Path
import dash
import plotly.graph_objects as go
from dash import html, dcc, callback, Output, State, Input, dash_table
from pandas import DataFrame
from ted_sws.data_manager.adapters.triple_store import FusekiAdapter

dash.register_page(__name__)

TED_DATA_MONGODB_DATABASE_NAME = 'ted_analytics'  # TODO: temporary while not put in config resolver
QUERY_FOLDER = 'sparql_queries'
TRIPLE_STORE_ENDPOINT_NAME = 'ted_data_dataset'
SPARQL_QUERY_FORMAT = '.rq'
FILES_ENCODING = 'utf-8'
QUERY_TIME_FORMAT = 'yyyy-mm-dd'
MIN_DATE = date(1995, 8, 5)
MAX_DATE = date(2030, 9, 19)
START_DATE = date(2020, 8, 5)
END_DATE = date(2022, 8, 25)

fuseki_adapter = FusekiAdapter()
fuseki_endpoint = fuseki_adapter.get_sparql_triple_store_endpoint(TRIPLE_STORE_ENDPOINT_NAME)


def figure_q14():
    collection_name = 'q14'
    query = Path(f'{QUERY_FOLDER}/{collection_name}{SPARQL_QUERY_FORMAT}').read_text(encoding=FILES_ENCODING)

    query_result: DataFrame = fuseki_endpoint.with_query(query).fetch_tabular()

    if query_result.empty:
        return go.Figure(go.Indicator())

    fig = go.Figure(go.Indicator(mode="number", value=query_result['Nr_of_SME'][0], title={"text": "Nr of SME"},
                                 delta={'position': "top", 'reference': 320}, domain={'x': [0, 1], 'y': [0, 1]}))
    return fig


@callback(
    Output('q15_graph', 'figure'),
    State('q15_graph', 'figure'),
    State('q15_daterange', 'start_date'),
    State('q15_daterange', 'end_date'),
    Input('q15_button', 'n_clicks'),
    prevent_initial_call=True,
)
def figure_q15(figure: dict = None, start_date: str = START_DATE.strftime(QUERY_TIME_FORMAT),
               end_date: str = END_DATE.strftime(QUERY_TIME_FORMAT), n_clicks: int = 0):
    collection_name = 'q15'
    query = Path(f'{QUERY_FOLDER}/{collection_name}{SPARQL_QUERY_FORMAT}').read_text(encoding=FILES_ENCODING)

    query = query.replace("(?ContractConclusionDate > '2000-01-01'", f"(?ContractConclusionDate > '{start_date}'")
    query = query.replace("?ContractConclusionDate < '2030-12-31'^^xsd:date",
                          f"?ContractConclusionDate < '{end_date}'^^xsd:date")

    query_result = fuseki_endpoint.with_query(query).fetch_tabular()

    awarded_notes = query_result['Total_Awardet_Lots'][0] if not query_result.empty else 0  # TODO: change to Awarded
    prev_value = 0
    if figure:
        prev_value = figure['data'][0]['value']

    fig = go.Figure(go.Indicator(mode="number+delta",
                                 value=awarded_notes,
                                 title={"text": "Total Awarded Lots"},
                                 delta={'position': "top", 'reference': prev_value},
                                 domain={'x': [0, 1], 'y': [0, 1]}))
    return fig


#
@callback(
    Output("q2_graph", "figure"),
    Input("q2_dropdown", "value")
)
def figure_q2(value):
    collection_name = 'q2'
    query = Path(f'{QUERY_FOLDER}/{collection_name}{SPARQL_QUERY_FORMAT}').read_text(encoding=FILES_ENCODING)
    query_result = fuseki_endpoint.with_query(query).fetch_tabular()

    if query_result.empty:
        return go.Figure(go.Pie(labels=['Empty'], values=[1]))

    fig = go.Figure(
        go.Pie(labels=list(query_result['Winner_Country']), values=list(query_result['Lots_using_EU_Funds']))
    )
    return fig


def figure_q3():
    collection_name = 'q3'
    query = Path(f'{QUERY_FOLDER}/{collection_name}{SPARQL_QUERY_FORMAT}').read_text(encoding=FILES_ENCODING)
    query_result = fuseki_endpoint.with_query(query).fetch_tabular()

    return dash_table.DataTable(query_result.to_dict('records'), [{"name": i, "id": i} for i in query_result.columns])


layout = html.Div(children=[

    html.Center(children=[
        html.H1(children='POC of queries'),
        html.Br(),

        # Q14
        html.Div(children=[
            dcc.Graph(figure=figure_q14()),
        ], style={"border": "2px black solid"}),

        # Q15
        html.Div(children=[
            dcc.Graph(id='q15_graph', figure=figure_q15()),
            dcc.DatePickerRange(
                id='q15_daterange',
                min_date_allowed=MIN_DATE,
                max_date_allowed=MAX_DATE,
                start_date=START_DATE,
                end_date=END_DATE
            ),
            html.Button('Submit', id='q15_button', n_clicks=0),
        ], style={'display': 'inline-block', "margin-left": "15px", "border": "2px black solid"}),

        # Q2
        html.Div(children=[
            html.H1("Lots using EU Funds per winner country"),
            dcc.Graph(id="q2_graph", style={"height": "600px", "width": "100%"}),
            html.Br(),
            # TODO: somehow add elements from query
            dcc.Dropdown(['Empty'], multi=True, id="q2_dropdown",
                         style={"height": "50%", "width": "50%"})
        ], style={"border": "2px black solid"}),

        # Q3
        html.Div(children=[
            figure_q3(),
        ], style={"border": "2px black solid"}),

    ])

], style={'display': "flex", "align-items": "center", "justify-content": "center"})
