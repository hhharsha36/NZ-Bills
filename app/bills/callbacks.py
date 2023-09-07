from datetime import datetime
import logging
import os

import calendar
from dash import dcc, html, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from flask import render_template
from flask_login import current_user
import numpy as np
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

from app.bills.internal import email_image, get_pm_data, update_usr_session, get_usr_from_db, SIZE_RANGE
from app.bills.internal import get_last_session, YEAR_RANGE


# TODO: save and read from DynamoDB DONE!!!
# COLOUR_DISCRETION_MAP = {
#     '(?)': 'Purple',
#     'Chris Hipkins (Labour Party)': 'Maroon',
#     'Jacinda Ardern (Labour Party)': 'Red',
#     'Bill English (National Party)': 'RoyalBlue',
#     'John Key (National Party)': 'MediumSlateBlue',
#     'Helen Clark (Labour Party)': 'Tomato',
# }

PM_DETAILS = get_pm_data()
colour_discretion_map = {f"{d['name']} ({d['party']})": d['colour'] for d in PM_DETAILS}
colour_discretion_map['(?)'] = 'Purple'

# TODO: review year start data, confirm that it is from year 2008
year_range = YEAR_RANGE

DEFAULT_VALUES = {
    'pie_order': 'By Time',
    'include_other': "No",
    'time_period_range': [min(year_range), max(year_range)],
    'size_range': 1_600
}


def is_default(pie_order, include_other, time_period_range, size_range):
    cmp_dict = {
        'pie_order': pie_order,
        'include_other': include_other,
        'time_period_range': time_period_range,
        'size_range': size_range
    }
    logging.debug(f'{cmp_dict=}')
    logging.debug(f'{DEFAULT_VALUES=}')
    return DEFAULT_VALUES == cmp_dict


def read_pd_from_csv():
    csv_path = os.path.join(os.path.dirname(__file__), 'parsedData.csv')
    tmp_df = pd.read_csv(csv_path)

    tmp_df['Last activity'] = pd.to_datetime(tmp_df['Last activity'])
    tmp_df.drop('Stage', axis=1, inplace=True)
    tmp_df.drop('Unnamed: 0', axis=1, inplace=True)
    tmp_df['year'] = pd.DatetimeIndex(tmp_df['Last activity']).year
    tmp_df['month'] = pd.DatetimeIndex(tmp_df['Last activity']).month
    tmp_df['month'] = tmp_df['month'].apply(lambda x: calendar.month_name[x])
    tmp_df['Committee'] = tmp_df['Select Committee'].fillna('Other')
    tmp_df['image'] = 'New Zealand - Bills Passed (Time)'
    # TODO: store and retrieve this data from DB
    for pm_details in PM_DETAILS:
        tmp_df.loc[
            tmp_df['Last activity'] <= datetime.fromtimestamp(pm_details['term']), 'PM'
        ] = f"{pm_details['name']} ({pm_details['party']})"
    # tmp_df.loc[tmp_df['Last activity'] <= datetime(2024, 1, 25), 'PM'] = 'Chris Hipkins (Labour Party)'
    # tmp_df.loc[tmp_df['Last activity'] <= datetime(2023, 1, 24), 'PM'] = 'Jacinda Ardern (Labour Party)'
    # tmp_df.loc[tmp_df['Last activity'] <= datetime(2017, 11, 26), 'PM'] = 'Bill English (National Party)'
    # tmp_df.loc[tmp_df['Last activity'] <= datetime(2016, 12, 12), 'PM'] = 'John Key (National Party)'
    # tmp_df.loc[tmp_df['Last activity'] <= datetime(2008, 11, 19), 'PM'] = 'Helen Clark (Labour Party)'
    tmp_df.drop('Select Committee', axis=1, inplace=True)
    tmp_df.sort_values(by=['Last activity'], ascending=[True], na_position='first')

    global year_range
    year_range = tmp_df['year'].unique()

    tmp_timeperiod_df = tmp_df.copy()
    tmp_timeperiod_df['Committee_no_other'] = tmp_timeperiod_df['Committee']
    tmp_timeperiod_df.loc[tmp_timeperiod_df["Committee_no_other"] == "Other", "Committee_no_other"] = np.NaN
    # logging.debug(tmp_timeperiod_df.head())
    tmp_timeperiod_non_other_df = tmp_df.copy()
    tmp_timeperiod_non_other_df.drop(
        tmp_timeperiod_non_other_df[tmp_timeperiod_non_other_df['Committee'] == 'Other'].index, inplace=True)

    tmp_category_df = tmp_df.copy()
    # logging.debug(tmp_category_df.head())
    tmp_category_df.drop(tmp_category_df[tmp_category_df['Committee'] == 'Other'].index, inplace=True)
    return tmp_df, tmp_timeperiod_df, tmp_timeperiod_non_other_df, tmp_category_df


df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()


def get_fig(source_data: pd.DataFrame, size: int):
    fig = go.Figure(px.sunburst(data_frame=source_data, path=['image', 'year', 'month', 'Committee', 'Name of bill'],
                                width=size, height=size, maxdepth=4, color='PM',
                                color_discrete_map=colour_discretion_map))

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


def get_fig_pm_priority(source_data: pd.DataFrame, size: int):
    category_fig = px.sunburst(data_frame=source_data, path=['image', 'Committee', 'PM', 'Name of bill'],
                               width=size, height=size, maxdepth=4, color='Committee')

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


def refresh_df():
    global df, timeperiod_df, timeperiod_non_other_df, category_df
    df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()


def bills_register_dash_components(app):
    # fig_size = 1_600
    refresh_df()
    global df, timeperiod_df, timeperiod_non_other_df, category_df
    # number_of_refresh_clicks = 0

    app.title = "Information Visualisation - Project"
    app.layout = html.Div(children=[
        html.H1(
            children='New Zealand - Visualisation of Bills Passed Over the Years',
            style={'font-family': 'Verdana'},
        ),

        # dbc.Alert(
        #     "Error",
        #     id="alert-danger",
        #     is_open=False,
        #     duration=4000,
        #     color="danger"
        # ),

        dbc.Row(
            [
                html.Div([
                    html.A(
                        html.Button(
                            "Log Out",
                            # style={"transition-duration": "0.4s", "hover.background-color": "#4CAF50"}
                            style={
                                "background-color": "#f44336",
                                "color": "white",
                                "border": "2px solid red",
                                "border-radius": "2px",
                                "font-size": "16px",
                                "padding": "10px 24px",
                                "transition-duration": "0.4s",
                                ":hover": {
                                    "background-color": "#4CAF50",
                                    "color": "black",
                                },
                            }
                        ),
                        href="/logout"
                    )
                ],
                    style={"margin-left": "20px", 'width': '10%', 'float': 'right', 'display': 'inline-block',
                           'font-family': 'Verdana'}
                ),

                html.Div(
                    children='''New Zealand - Bills Passed in parliament from September, 2002 to Present. Use the below multiple 
                            filter options available to fine tune the visualisation as per your need.''',
                    style={'font-family': 'Verdana'},
                ),
            ]
        ),

        html.Br(),
        html.Br(),

        dbc.Row([
            dbc.Col(html.Div([
                html.P('Change Nested Chart Index By:', style={'font-family': 'Verdana'}, ),
                dcc.Dropdown(
                    ['By Time', 'By Prime Minister', 'By Category Priority'],
                    # TODO: what is the below line for?
                    'Chart Index',
                    searchable=False,
                    placeholder="View Chart Index By",
                    id='pie-order'
                ),
            ],
                style={'width': '20%', 'float': 'left', 'display': 'inline-block'}
            ),
                width={"order": 1}
            ),

            dbc.Col(html.Div([
                html.P('''View 'Other' category Bills:''', style={'font-family': 'Verdana', "margin-bottom": "25px"}, ),
                dcc.RadioItems(
                    ['Yes', 'No'],
                    '''Show 'Other' Committee''',
                    id='include-other',
                    inline=True,
                    style={"margin-bottom": "30px"},
                )
            ],
                style={"margin-left": "100px", 'width': '20%', 'float': 'left', 'display': 'inline-block',
                       'font-family': 'Verdana'}
            ),
                width={"order": 2}
            ),

            # dbc.Col(
            #     dbc.Row([
                    dbc.Col(
                        # html.Div([
                        dbc.Row([
                            dbc.Col(
                                html.Div([
                                    html.Button(
                                        'Email Visualisation',
                                        id='button-email-visualisation',
                                        style={
                                            "background-color": "#4CAF50",
                                            "color": "white",
                                            "border": "2px solid #4CAF50",
                                            "border-radius": "2px",
                                            "font-size": "16px",
                                            "padding": "10px 24px",
                                            "transition-duration": "0.4s",
                                            ":hover": {
                                                "background-color": "#4CAF50",
                                                "color": "black",
                                            },
                                        }
                                    ),
                                    dbc.Alert(
                                        children="Successfully Logged in!",
                                        id="alert",
                                        is_open=True,
                                        duration=3000,
                                        color="success"
                                    ),
                                ]),
                                width={"order": 1}
                            ),
                            dbc.Col(
                                html.Div([
                                    html.Button(
                                        'Reset Visualisation',
                                        id='button-reset-visualisation',
                                        style={
                                            "background-color": "#008CBA",
                                            "color": "white",
                                            "border": "2px solid #008CBA",
                                            "border-radius": "2px",
                                            "font-size": "16px",
                                            "padding": "10px 24px",
                                            "transition-duration": "0.4s",
                                            ":hover": {
                                                "background-color": "#4CAF50",
                                                "color": "black",
                                            },
                                        }
                                    ),
                                    # html.Div(id='reset-container-button', children=html.Br())
                                ], style={
                                    "margin-top": "10px"
                                }),
                                width={"order": 2}
                            )
                        ]),
                    # ]),),
                    #     dbc.Row([
                    #         html.Div([
                    #             html.Button(
                    #                 'Reset Visualisation',
                    #                 id='button-save-visualisation',
                    #                 style={
                    #                     "background-color": "#4CAF50",
                    #                     "color": "white",
                    #                     "border": "2px solid #4CAF50",
                    #                     "border-radius": "2px",
                    #                     "font-size": "16px",
                    #                     "padding": "10px 24px",
                    #                     "transition-duration": "0.4s",
                    #                     ":hover": {
                    #                         "background-color": "#4CAF50",
                    #                         "color": "black",
                    #                     },
                    #                 }
                    #             ),
                    #             html.Div(id='save-container-button', children='')
                    #         ], style={
                    #             "margin-top": "10px"
                    #         }),
                    #     ]),
                    # ],),
                        width={"order": 3}
                    ),
            #     ])
            # ),
        ]),


        # html.Br(),



        # html.Div([
        #     # TODO: implement function to email upon click
        #     html.P('''Click on the below button to email data'''),
        #     # DEPRECATED!
        #     # html.Button('Refresh Data', id='refresh-data', n_clicks=0),  # TODO: check `n_clicks` functionality
        #     html.Button(
        #         "Email Visualisation",
        #         style={
        #             "background-color": "#4CAF50",
        #             "color": "white",
        #             "border": "2px solid #4CAF50",
        #             "border-radius": "2px",
        #             "font-size": "16px",
        #             "padding": "10px 24px",
        #             "transition-duration": "0.4s",
        #             ":hover": {
        #                 "background-color": "#4CAF50",
        #                 "color": "black",
        #             },
        #         }
        #     )
        # ],
        #     style={"margin-left": "100px", 'width': '20%', 'float': 'left', 'display': 'inline-block',
        #            'font-family': 'Verdana'}
        # ),

        html.Div([
            html.P('''Use the below slider to filter year range:''', style={'font-family': 'Verdana'}, ),
            dcc.RangeSlider(min(year_range), max(year_range), step=1,
                            # marks=None,
                            marks={int(i): f'{int(i)}' for i in year_range},
                            value=[min(year_range), max(year_range)],
                            tooltip={"placement": "bottom", "always_visible": True},
                            allowCross=False,
                            id='year-range'),
        ],
            style={"margin-top": "100px", 'width': '100%', 'font-family': 'Verdana'},
        ),
        html.Div([
            html.P('''Use the below slider to modify the visualisation size:''', style={'font-family': 'Verdana'}, ),
            dcc.Slider(1000, 2500, step=100,
                       marks={int(i): f'{int(i)}' for i in SIZE_RANGE},
                       value=DEFAULT_VALUES['size_range'],
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
            figure=get_fig(source_data=timeperiod_df, size=DEFAULT_VALUES['size_range']),
            style={"margin-top": "1px"},
        ),

        html.Div(
            children='''This Visualisation was done by Harshavardhan as a project made for the Information Visualisation 
            (COMPX532) paper handled by Professor Dr. Mark Apperley at the University of Waikato, Hamilton.''',
            style={'font-family': 'Verdana'},
        ),

    ])

    @app.callback(
        Output('NZ-bills-passed', 'figure', allow_duplicate=True),
        Output('pie-order', 'value', allow_duplicate=True),
        Output('include-other', 'value', allow_duplicate=True),
        Output('year-range', 'value', allow_duplicate=True),
        Output('size-range', 'value', allow_duplicate=True),
        Input('pie-order', 'value'),
        Input('include-other', 'value'),
        # Input('refresh-data', 'n_clicks'),
        Input('year-range', 'value'),
        Input('size-range', 'value'),
        prevent_initial_call=True
    )
    # def update_graph(pie_order, include_other, n_clicks, time_period_range, size_range):
    def update_graph(pie_order, include_other, time_period_range, size_range):
        # if not n_clicks:
        #     return dash.no_update

        # global df, timeperiod_df, timeperiod_non_other_df, category_df, number_of_refresh_clicks
        # if n_clicks > number_of_refresh_clicks:
        #     df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()
        #     number_of_refresh_clicks = n_clicks
        logging.debug(f'{pie_order=}, {include_other=}, {time_period_range=}, {size_range=}')

        # if not pie_order:
        #     pie_order = 'By Time'
        if include_other == "Show 'Other' Committee":
            include_other = 'No'
        logging.debug(f'{ctx.triggered_id=}; {pie_order=}')

        db_update = True
        if ctx.triggered_id == 'pie-order' and not pie_order:
            pie_order = 'By Time'
            include_other = 'No'
        # if is_default(pie_order, include_other, time_period_range, size_range):
            logging.debug(f'is default')
            # TODO: get user data from DB
            if not current_user.is_authenticated:
                return render_template('login.html')
            last_session = get_last_session(current_user.name)
            if last_session:
                db_update = False
                logging.info(f'restoring last session for user: {current_user.name}')
                pie_order = last_session['pie_order']
                include_other = last_session['include_other']
                time_period_range = last_session['time_period_range']
                size_range = last_session['size_range']
            else:
                logging.info(f'last session same as current session for user: {current_user.name}; {last_session=}')

        if db_update:
            logging.info(f'performing db update for user: {current_user.name}')
            update_usr_session(
                username=current_user.name,
                session_details={
                    'pie_order': pie_order,
                    'include_other': include_other,
                    'time_period_range': time_period_range,
                    'size_range': size_range,
                }
            )

        if include_other == 'Yes':
            include_other_opt = timeperiod_df.copy()
        else:
            include_other_opt = timeperiod_non_other_df.copy()

        if isinstance(time_period_range, list) and len(time_period_range) == 2:
            include_other_opt = include_other_opt[
                (include_other_opt['year'] >= min(time_period_range)) & (
                        include_other_opt['year'] <= max(time_period_range))]

            if pie_order == 'By Prime Minister':
                return get_fig_pm(source_data=include_other_opt, size=size_range), pie_order, include_other, \
                    time_period_range, size_range
            elif pie_order == 'By Category Priority':
                return get_fig_pm_priority(source_data=include_other_opt, size=size_range), pie_order, include_other, \
                    time_period_range, size_range
        return get_fig(source_data=include_other_opt, size=size_range), pie_order, include_other, \
            time_period_range, size_range

    @app.callback(
        # Output('alert', 'is_open'),
        Output('alert', 'children'),
        Output('alert', 'is_open'),
        Output('alert', 'color'),
        Input('button-email-visualisation', 'n_clicks'),
        # State('email-input-box', 'value'),
        # State('alert', 'is_open'),
        # State('alert', 'is_open', 'color'),
    )
    def email_fig(n_clicks):
        logging.debug(f'email called')
        if not n_clicks:
            return no_update
        is_open = True
        color = 'danger'
        if not current_user.is_authenticated:
            children = 'not logged in'
            return children, is_open, color

        if email_image(recipient=current_user, img_path=''):
            children = f'successfully sent email on: {datetime.now()}'
            color = 'success'
            return children, is_open, color
        children = 'error sending email'
        return children, is_open, color

    @app.callback(
        # Output('reset-container-button', 'children'),
        Output('NZ-bills-passed', 'figure'),
        Output('pie-order', 'value'),
        Output('include-other', 'value'),
        Output('year-range', 'value'),
        Output('size-range', 'value'),
        Input('button-reset-visualisation', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_fig(n_clicks):
        if not n_clicks:
            return tuple([no_update] * 5)
        if not update_usr_session(username=current_user.name, session_details=DEFAULT_VALUES):
            return tuple([no_update] * 5)
        return get_fig(
            source_data=timeperiod_non_other_df.copy(), size=DEFAULT_VALUES['size_range']
        ), DEFAULT_VALUES['pie_order'], DEFAULT_VALUES['include_other'], DEFAULT_VALUES['time_period_range'], \
            DEFAULT_VALUES['size_range']
        # return f'Saved to DB on: {datetime.now().isoformat()}'


if __name__ == '__main__':
    import dash
    dash_app = dash.Dash(__name__, requests_pathname_prefix='/')
    dash_app.config.suppress_callback_exceptions = True
    bills_register_dash_components(dash_app)
    dash_app.run_server(debug=True)
