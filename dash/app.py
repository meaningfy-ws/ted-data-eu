import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.GRID])
server = app.server

app.layout = html.Div([

    dash.page_container
])

if __name__ == '__main__':
    app.run_server(debug=True)
