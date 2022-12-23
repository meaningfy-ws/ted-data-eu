import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

load_figure_template('FLATLY')
app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

app.layout = html.Div([

    dash.page_container
])

if __name__ == '__main__':
    app.run_server(debug=True)
