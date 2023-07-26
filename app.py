import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from datetime import datetime
import calendar
import plotly.graph_objects as go
import numpy as np
from parse_data_func import UpdateData

app = dash.Dash(__name__)

FIG_SIZE = 1500
COLOUR_DISCRETION_MAP = {
    '(?)': 'Purple',
    'Jacinda Ardern (Labour Party)': 'Red',
    'Bill English (National Party)': 'RoyalBlue',
    'John Key (National Party)': 'MediumSlateBlue',
    'Helen Clark (Labour Party)': 'Tomato',
}

update_data = UpdateData()
number_of_refresh_clicks = 0
year_range = [*range(2008, 2023)]


def read_pd_from_csv():
    tmp_df = pd.read_csv('parsedData.csv')

    tmp_df['Last activity'] = pd.to_datetime(tmp_df['Last activity'])
    tmp_df.drop('Stage', axis=1, inplace=True)
    tmp_df.drop('Unnamed: 0', axis=1, inplace=True)
    tmp_df['year'] = pd.DatetimeIndex(tmp_df['Last activity']).year
    tmp_df['month'] = pd.DatetimeIndex(tmp_df['Last activity']).month
    tmp_df['month'] = tmp_df['month'].apply(lambda x: calendar.month_name[x])
    tmp_df['Committee'] = tmp_df['Select Committee'].fillna('Other')
    tmp_df['image'] = 'New Zealand - Bills Passed (Time)'
    tmp_df.loc[tmp_df['Last activity'] <= datetime(2023, 11, 26), 'PM'] = 'Jacinda Ardern (Labour Party)'
    tmp_df.loc[tmp_df['Last activity'] <= datetime(2017, 11, 26), 'PM'] = 'Bill English (National Party)'
    tmp_df.loc[tmp_df['Last activity'] <= datetime(2016, 12, 12), 'PM'] = 'John Key (National Party)'
    tmp_df.loc[tmp_df['Last activity'] <= datetime(2008, 11, 19), 'PM'] = 'Helen Clark (Labour Party)'
    tmp_df.drop('Select Committee', axis=1, inplace=True)
    tmp_df.sort_values(by=['Last activity'], ascending=[True], na_position='first')

    global year_range
    year_range = tmp_df['year'].unique()

    tmp_timeperiod_df = tmp_df.copy()
    tmp_timeperiod_df['Committee_no_other'] = tmp_timeperiod_df['Committee']
    tmp_timeperiod_df.loc[tmp_timeperiod_df["Committee_no_other"] == "Other", "Committee_no_other"] = np.NaN
    print(tmp_timeperiod_df.head())
    tmp_timeperiod_non_other_df = tmp_df.copy()
    tmp_timeperiod_non_other_df.drop(
        tmp_timeperiod_non_other_df[tmp_timeperiod_non_other_df['Committee'] == 'Other'].index, inplace=True)

    tmp_category_df = tmp_df.copy()
    print(tmp_category_df.head())
    tmp_category_df.drop(tmp_category_df[tmp_category_df['Committee'] == 'Other'].index, inplace=True)
    return tmp_df, tmp_timeperiod_df, tmp_timeperiod_non_other_df, tmp_category_df


df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()


def get_fig(source_data: pd.DataFrame, size: int):
    fig = go.Figure(px.sunburst(data_frame=source_data, path=['image', 'year', 'month', 'Committee', 'Name of bill'],
                                width=size, height=size, maxdepth=4, color='PM',
                                color_discrete_map=COLOUR_DISCRETION_MAP))

    fig.update_layout(
        updatemenus=[
            dict(
                buttons=list([
                    dict(
                        args=["maxdepth", 4],
                        label="4",
                        method="restyle"
                    ),
                    dict(
                        args=["maxdepth", 3],
                        label="3",
                        method="restyle"
                    )
                ]),
                type="buttons",
                direction="right",
                pad={"r": 100, "t": 100},
                showactive=True,
                x=1,
                xanchor="left",
                y=1.08,
                yanchor="top"
            ),
        ]
    )

    fig.update_layout(
        annotations=[
            dict(text="Max. Depth", x=0, xref="paper", y=1.1, yref="paper", align="left", showarrow=False),
        ])
    return fig


def get_fig_pm(source_data: pd.DataFrame, size: int):
    category_fig = px.sunburst(data_frame=source_data, path=['image', 'PM', 'Committee', 'Name of bill'],
                               width=size, height=size, maxdepth=3, color='Committee')

    category_fig.update_layout(
        updatemenus=[
            dict(
                buttons=list([
                    dict(
                        args=["maxdepth", 3],
                        label="2",
                        method="restyle"
                    ),
                    dict(
                        args=["maxdepth", 4],
                        label="3",
                        method="restyle"
                    ),
                ]),
                type="buttons",
                direction="left",
            ),
        ]
    )

    return category_fig


app.title = "Information Visualisation - Project"
app.layout = html.Div(children=[
    html.H1(
        children='New Zealand - Visualisation of Bills Passed Over the Years',
        style={'font-family': 'Verdana'},
    ),

    html.Div(
        children='''New Zealand - Bills Passed in parliament from September, 2002 to Present. Use the below multiple 
        filter options available to fine tune the visualisation as per your need.''',
        style={'font-family': 'Verdana'},
    ),

    html.Br(),
    html.Br(),

    html.Div([
        html.P('Change Nested Chart Index By:', style={'font-family': 'Verdana'},),
        dcc.Dropdown(
            ['By Time', 'By Prime Minister'],
            'Life expectancy at birth, total (years)',
            searchable=False,
            placeholder="View Chart Index By",
            id='pie-order'
        ),
    ],
        style={'width': '20%', 'float': 'left', 'display': 'inline-block'}
    ),
    # html.Br(),
    html.Div([
        html.P('''View 'Other' category Committees:''', style={'font-family': 'Verdana'},),
        dcc.RadioItems(
            ['Yes', 'No'],
            '''Show 'Other' Committee''',
            id='include-other',
            inline=True
        )
    ],
        style={"margin-left": "100px", 'width': '20%', 'float': 'left', 'display': 'inline-block',
               'font-family': 'Verdana'}
    ),
    html.Div([
        html.P('''Click on the below button to refresh data'''),
        html.Button('Refresh Data', id='refresh-data', n_clicks=0),  # TODO: check `n_clicks` functionality
    ],
        style={"margin-left": "100px", 'width': '20%', 'float': 'left', 'display': 'inline-block',
               'font-family': 'Verdana'}
    ),

    html.Div([
        html.P('''Use the below slider to filter year range:''', style={'font-family': 'Verdana'},),
        dcc.RangeSlider(min(year_range), max(year_range), step=1,
                        # marks=None,
                        value=[min(year_range), max(year_range)],
                        tooltip={"placement": "bottom", "always_visible": True},
                        allowCross=False, id='year-range'),
    ],
        style={"margin-top": "100px", 'width': '100%', 'font-family': 'Verdana'},
    ),
    html.Div([
        html.P('''Use the below slider to modify the visualisation size:''', style={'font-family': 'Verdana'},),
        dcc.Slider(1000, 2500, step=100,
                   value=FIG_SIZE,
                   tooltip={"placement": "bottom", "always_visible": True},
                   id='size-range'),
    ],
        style={'width': '100%', 'font-family': 'Verdana'},
    ),

    html.Br(),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Br(),

    dcc.Graph(
        id='NZ-bills-passed',
        figure=get_fig(source_data=timeperiod_df, size=FIG_SIZE),
        style={"margin-top": "1px"},
    ),

    html.Div(
        children='''This Visualisation was done by Harshavardhan as a project made for the Information Visualisation 
        (COMPX532) paper handled by Professor Dr. Mark Apperley at the University of Waikato, Hamilton.''',
        style={'font-family': 'Verdana'},
    ),

])


@app.callback(
    Output('NZ-bills-passed', 'figure'),
    Input('pie-order', 'value'),
    Input('include-other', 'value'),
    Input('refresh-data', 'n_clicks'),
    Input('year-range', 'value'),
    Input('size-range', 'value'), )
def update_graph(pie_order, include_other, n_clicks, time_period_range, size_range):
    global df, timeperiod_df, timeperiod_non_other_df, category_df, number_of_refresh_clicks
    if n_clicks > number_of_refresh_clicks:
        df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()
        number_of_refresh_clicks = n_clicks

    include_other_opt = timeperiod_non_other_df.copy()
    if include_other == 'Yes':
        include_other_opt = timeperiod_df.copy()

    print(f"{size_range=}")
    if isinstance(time_period_range, list) and len(time_period_range) == 2:
        include_other_opt = include_other_opt[
            (include_other_opt['year'] >= min(time_period_range)) & (
                    include_other_opt['year'] <= max(time_period_range))]

        if pie_order == 'By Prime Minister':
            return get_fig_pm(source_data=include_other_opt, size=size_range)

    return get_fig(source_data=include_other_opt, size=size_range)


if __name__ == '__main__':
    app.run_server(debug=True)
