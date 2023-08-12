from datetime import datetime
import logging
import os

import calendar
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from flask_login import current_user
import numpy as np
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

from app.bills.internal import get_pm_data, email_image, get_usr_from_db, update_usr_session_to_db


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
# colour_discretion_map = {f"{d['name']} ({d['party']})": d['colour'] for d in PM_DETAILS}
colour_discretion_map['(?)'] = 'Purple'

# TODO: review year start data, confirm that it is from year 2008
year_range = [*range(2002, datetime.now().year + 1)]

DEFAULT_VALUES = {
    'pie_order': None,
    'include_other': "Show 'Other' Committee",
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
    print(tmp_timeperiod_df.head())
    tmp_timeperiod_non_other_df = tmp_df.copy()
    tmp_timeperiod_non_other_df.drop(
        tmp_timeperiod_non_other_df[tmp_timeperiod_non_other_df['Committee'] == 'Other'].index, inplace=True)

    tmp_category_df = tmp_df.copy()
    print(tmp_category_df.head())
    tmp_category_df.drop(tmp_category_df[tmp_category_df['Committee'] == 'Other'].index, inplace=True)
    return tmp_df, tmp_timeperiod_df, tmp_timeperiod_non_other_df, tmp_category_df


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


def bills_register_dash_components(app):
    # fig_size = 1_600
    df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()
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
                    ['By Time', 'By Prime Minister'],
                    # TODO: what is the below line for?
                    'Life expectancy at birth, total (years)',
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
                       marks={int(i): f'{int(i)}' for i in range(100, 2500, 100)},
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
        Input('pie-order', 'value'),
        Input('include-other', 'value'),
        # Input('refresh-data', 'n_clicks'),
        Input('year-range', 'value'),
        Input('size-range', 'value'),
        # prevent_initial_call=True,
    )
    # def update_graph(pie_order, include_other, n_clicks, time_period_range, size_range):
    def update_graph(pie_order, include_other, time_period_range, size_range):
        # if not n_clicks:
        #     return dash.no_update

        # global df, timeperiod_df, timeperiod_non_other_df, category_df, number_of_refresh_clicks
        # if n_clicks > number_of_refresh_clicks:
        #     df, timeperiod_df, timeperiod_non_other_df, category_df = read_pd_from_csv()
        #     number_of_refresh_clicks = n_clicks

        logging.debug(f'{current_user.name=}')
        if is_default(pie_order, include_other, time_period_range, size_range):
            logging.debug(f'is default')
            user = get_usr_from_db(username=current_user.name)
            if user and user.get('RememberSession'):
                pie_order = user['RememberSession'].get('pie_order', DEFAULT_VALUES['pie_order'])
                include_other = user['RememberSession'].get('include_other', DEFAULT_VALUES['include_other'])
                time_period_range = user['RememberSession'].get('time_period_range', DEFAULT_VALUES['time_period_range'])
                size_range = user['RememberSession'].get('size_range', DEFAULT_VALUES['size_range'])
                logging.info(f'successfully restored last session')

        if include_other == 'Yes':
            include_other_opt = timeperiod_df.copy()
        else:
            include_other_opt = timeperiod_non_other_df.copy()

        if isinstance(time_period_range, list) and len(time_period_range) == 2:
            include_other_opt = include_other_opt[
                (include_other_opt['year'] >= min(time_period_range)) & (
                        include_other_opt['year'] <= max(time_period_range))]

            if pie_order == 'By Prime Minister':
                return get_fig_pm(source_data=include_other_opt, size=size_range)

        return get_fig(source_data=include_other_opt, size=size_range)

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
        # TODO: uncomment
        # if email_image(recipient=current_user, img_path=''):
        #     children = f'successfully sent email on: {datetime.now()}'
        #     color = 'success'
        #     return children, is_open, color
        children = 'error sending email'
        return children, is_open, color

    @app.callback(
        # Output('alert', 'children'),
        # Output('alert', 'is_open'),
        # Output('alert', 'color'),
        Output('NZ-bills-passed', 'figure'),
        Input('button-reset-visualisation', 'n_clicks'),
        # prevent_initial_call=True,
    )
    def reset_fig(n_clicks):
        if not n_clicks:
            return no_update
        if not current_user.is_authenticated:
            children = 'not logged in'
            is_open = True
            color = 'danger'
            return children, is_open, color

        update_usr_session_to_db(username=current_user.name, session_data=DEFAULT_VALUES)
        return get_fig(source_data=timeperiod_non_other_df.copy(), size=DEFAULT_VALUES['size_range'])


"<!doctype html>\n<html lang=en>\n  <head>\n    <title>botocore.exceptions.ParamValidationError: Parameter validation failed:\nUnknown parameter in AttributeUpdates.RememberSession: \"pie_order\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"include_other\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"time_period_range\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"size_range\", must be one of: Value, Action\n // Werkzeug Debugger</title>\n    <link rel=\"stylesheet\" href=\"?__debugger__=yes&amp;cmd=resource&amp;f=style.css\">\n    <link rel=\"shortcut icon\"\n        href=\"?__debugger__=yes&amp;cmd=resource&amp;f=console.png\">\n    <script src=\"?__debugger__=yes&amp;cmd=resource&amp;f=debugger.js\"></script>\n    <script>\n      var CONSOLE_MODE = false,\n          EVALEX = true,\n          EVALEX_TRUSTED = false,\n          SECRET = \"6RVSd6hPOKcsEFKvg3o7\";\n    </script>\n  </head>\n  <body style=\"background-color: #fff\">\n    <div class=\"debugger\">\n<h1>ParamValidationError</h1>\n<div class=\"detail\">\n  <p class=\"errormsg\">botocore.exceptions.ParamValidationError: Parameter validation failed:\nUnknown parameter in AttributeUpdates.RememberSession: &#34;pie_order&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;include_other&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;time_period_range&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;size_range&#34;, must be one of: Value, Action\n</p>\n</div>\n<h2 class=\"traceback\">Traceback <em>(most recent call last)</em></h2>\n<div class=\"traceback\">\n  <h3></h3>\n  <ul><li><div class=\"frame\" id=\"frame-5149016416\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">2552</em>,\n      in <code class=\"function\">__call__</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">    </span>def __call__(self, environ: dict, start_response: t.Callable) -&gt; t.Any:</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>&#34;&#34;&#34;The WSGI server calls the Flask application object as the</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>WSGI application. This calls :meth:`wsgi_app`, which can be</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>wrapped to apply middleware.</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>&#34;&#34;&#34;</pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>return self.wsgi_app(environ, start_response)\n<span class=\"ws\">        </span>       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147747824\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">2532</em>,\n      in <code class=\"function\">wsgi_app</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>try:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>ctx.push()</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>response = self.full_dispatch_request()</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>except Exception as e:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>error = e</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>response = self.handle_exception(e)\n<span class=\"ws\">                </span>           ^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>except:  # noqa: B001</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>error = sys.exc_info()[1]</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>raise</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>return response(environ, start_response)</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>finally:</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147747968\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">2529</em>,\n      in <code class=\"function\">wsgi_app</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">        </span>ctx = self.request_context(environ)</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>error: t.Optional[BaseException] = None</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>try:</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>try:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>ctx.push()</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>response = self.full_dispatch_request()\n<span class=\"ws\">                </span>           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>except Exception as e:</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>error = e</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>response = self.handle_exception(e)</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>except:  # noqa: B001</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>error = sys.exc_info()[1]</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147748112\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">1825</em>,\n      in <code class=\"function\">full_dispatch_request</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>request_started.send(self)</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>rv = self.preprocess_request()</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>if rv is None:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>rv = self.dispatch_request()</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>except Exception as e:</pre>\n<pre class=\"line current\"><span class=\"ws\">            </span>rv = self.handle_user_exception(e)\n<span class=\"ws\">            </span>     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return self.finalize_request(rv)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>def finalize_request(</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>self,</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>rv: t.Union[ft.ResponseReturnValue, HTTPException],</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147748256\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">1823</em>,\n      in <code class=\"function\">full_dispatch_request</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>try:</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>request_started.send(self)</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>rv = self.preprocess_request()</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>if rv is None:</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>rv = self.dispatch_request()\n<span class=\"ws\">                </span>     ^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>except Exception as e:</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>rv = self.handle_user_exception(e)</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return self.finalize_request(rv)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>def finalize_request(</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147748400\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\"</cite>,\n      line <em class=\"line\">1799</em>,\n      in <code class=\"function\">dispatch_request</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>and req.method == &#34;OPTIONS&#34;</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>):</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>return self.make_default_options_response()</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span># otherwise dispatch to the handler for that endpoint</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>view_args: t.Dict[str, t.Any] = req.view_args  # type: ignore[assignment]</pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)\n<span class=\"ws\">        </span>       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>def full_dispatch_request(self) -&gt; Response:</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>&#34;&#34;&#34;Dispatches the request and on top of that performs request</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>pre and postprocessing as well as HTTP exception catching and</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>error handling.</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147748544\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask_login/utils.py\"</cite>,\n      line <em class=\"line\">290</em>,\n      in <code class=\"function\">decorated_view</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>return current_app.login_manager.unauthorized()</pre>\n<pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line before\"><span class=\"ws\">        </span># flask 1.x compatibility</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span># current_app.ensure_sync is only available in Flask &gt;= 2.0</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>if callable(getattr(current_app, &#34;ensure_sync&#34;, None)):</pre>\n<pre class=\"line current\"><span class=\"ws\">            </span>return current_app.ensure_sync(func)(*args, **kwargs)\n<span class=\"ws\">            </span>       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return func(*args, **kwargs)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>return decorated_view</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5147750272\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/dash.py\"</cite>,\n      line <em class=\"line\">1265</em>,\n      in <code class=\"function\">dispatch</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>msg = f&#34;Callback function not found for output &#39;{output}&#39;, perhaps you forgot to prepend the &#39;@&#39;?&#34;</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>raise KeyError(msg) from missing_callback_function</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>ctx = copy_context()</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span># noinspection PyArgumentList</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>response.set_data(</pre>\n<pre class=\"line current\"><span class=\"ws\">            </span>ctx.run(\n<span class=\"ws\">            </span>^</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>functools.partial(</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span>func,</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span>*args,</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span>outputs_list=outputs_list,</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span>long_callback_manager=self._background_manager,</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148108704\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/_callback.py\"</cite>,\n      line <em class=\"line\">450</em>,\n      in <code class=\"function\">add_context</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>if output_value is callback_manager.UNDEFINED:</pre>\n<pre class=\"line before\"><span class=\"ws\">                    </span>return to_json(response)</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>else:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span># don&#39;t touch the comment on the next line - used by debugger</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>output_value = func(*func_args, **func_kwargs)  # %% callback invoked %%\n<span class=\"ws\">                </span>               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>if NoUpdate.is_no_update(output_value):</pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>raise PreventUpdate</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>if not multi:</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148114320\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/Developer/NZ-Bills/app/bills/callbacks.py\"</cite>,\n      line <em class=\"line\">509</em>,\n      in <code class=\"function\">reset_fig</code></h4>\n  <div class=\"source \"><pre class=\"line before\"><span class=\"ws\">            </span>children = &#39;not logged in&#39;</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>is_open = True</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>color = &#39;danger&#39;</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>return children, is_open, color</pre>\n<pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>update_usr_session_to_db(username=current_user.name, session_data=DEFAULT_VALUES)\n<span class=\"ws\">        </span>^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return get_fig(source_data=timeperiod_non_other_df.copy(), size=DEFAULT_VALUES[&#39;size_range&#39;])</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\"></span>if __name__ == &#39;__main__&#39;:</pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>import dash</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148248960\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/Developer/NZ-Bills/app/bills/internal.py\"</cite>,\n      line <em class=\"line\">77</em>,\n      in <code class=\"function\">update_usr_session_to_db</code></h4>\n  <div class=\"source \"><pre class=\"line before\"><span class=\"ws\">        </span>return None</pre>\n<pre class=\"line before\"><span class=\"ws\">    </span>return response</pre>\n<pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line before\"><span class=\"ws\"></span>def update_usr_session_to_db(username: str, session_data: dict):</pre>\n<pre class=\"line current\"><span class=\"ws\">    </span>USERS_TABLE.update_item(\n<span class=\"ws\">    </span>^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>Key={&#39;Username&#39;: username},</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>AttributeUpdates={</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>&#39;RememberSession&#39;: session_data,</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>},</pre>\n<pre class=\"line after\"><span class=\"ws\">    </span>)</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148249392\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/factory.py\"</cite>,\n      line <em class=\"line\">580</em>,\n      in <code class=\"function\">do_action</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>)</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>else:</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span># We need a new method here because we want access to the</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span># instance via ``self``.</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>def do_action(self, *args, **kwargs):</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>response = action(self, *args, **kwargs)\n<span class=\"ws\">                </span>           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">                </span>if hasattr(self, &#39;load&#39;):</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span># Clear cached data. It will be reloaded the next</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span># time that an attribute is accessed.</pre>\n<pre class=\"line after\"><span class=\"ws\">                    </span># TODO: Make this configurable in the future?</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148249824\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/action.py\"</cite>,\n      line <em class=\"line\">88</em>,\n      in <code class=\"function\">__call__</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>parent.meta.service_name,</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>operation_name,</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>params,</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>)</pre>\n<pre class=\"line before\"><span class=\"ws\"></span> </pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>response = getattr(parent.meta.client, operation_name)(*args, **params)\n<span class=\"ws\">        </span>           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>logger.debug(&#39;Response: %r&#39;, response)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return self._response_handler(parent, params, response)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148250112\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\"</cite>,\n      line <em class=\"line\">535</em>,\n      in <code class=\"function\">_api_call</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>if args:</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>raise TypeError(</pre>\n<pre class=\"line before\"><span class=\"ws\">                    </span>f&#34;{py_operation_name}() only accepts keyword arguments.&#34;</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>)</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span># The &#34;self&#34; in this scope is referring to the BaseClient.</pre>\n<pre class=\"line current\"><span class=\"ws\">            </span>return self._make_api_call(operation_name, kwargs)\n<span class=\"ws\">            </span>       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>_api_call.__name__ = str(py_operation_name)</pre>\n<pre class=\"line after\"><span class=\"ws\"></span> </pre>\n<pre class=\"line after\"><span class=\"ws\">        </span># Add the docstring to the client method</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>operation_model = service_model.operation_model(operation_name)</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148251408\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\"</cite>,\n      line <em class=\"line\">936</em>,\n      in <code class=\"function\">_make_api_call</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">            </span>context=request_context,</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>)</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>endpoint_url, additional_headers = self._resolve_endpoint_ruleset(</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>operation_model, api_params, request_context</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>)</pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>request_dict = self._convert_to_request_dict(\n<span class=\"ws\">        </span>               </pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>api_params=api_params,</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>operation_model=operation_model,</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>endpoint_url=endpoint_url,</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>context=request_context,</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>headers=additional_headers,</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148251552\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\"</cite>,\n      line <em class=\"line\">1007</em>,\n      in <code class=\"function\">_convert_to_request_dict</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">        </span>endpoint_url,</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>context=None,</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>headers=None,</pre>\n<pre class=\"line before\"><span class=\"ws\">        </span>set_user_agent_header=True,</pre>\n<pre class=\"line before\"><span class=\"ws\">    </span>):</pre>\n<pre class=\"line current\"><span class=\"ws\">        </span>request_dict = self._serializer.serialize_to_request(\n<span class=\"ws\">        </span>               </pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>api_params, operation_model</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>)</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>if not self._client_config.inject_host_prefix:</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>request_dict.pop(&#39;host_prefix&#39;, None)</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>if headers is not None:</pre></div>\n</div>\n\n<li><div class=\"frame\" id=\"frame-5148251696\">\n  <h4>File <cite class=\"filename\">\"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/validate.py\"</cite>,\n      line <em class=\"line\">381</em>,\n      in <code class=\"function\">serialize_to_request</code></h4>\n  <div class=\"source library\"><pre class=\"line before\"><span class=\"ws\">        </span>if input_shape is not None:</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>report = self._param_validator.validate(</pre>\n<pre class=\"line before\"><span class=\"ws\">                </span>parameters, operation_model.input_shape</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>)</pre>\n<pre class=\"line before\"><span class=\"ws\">            </span>if report.has_errors():</pre>\n<pre class=\"line current\"><span class=\"ws\">                </span>raise ParamValidationError(report=report.generate_report())\n<span class=\"ws\">                </span>^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>return self._serializer.serialize_to_request(</pre>\n<pre class=\"line after\"><span class=\"ws\">            </span>parameters, operation_model</pre>\n<pre class=\"line after\"><span class=\"ws\">        </span>)</pre></div>\n</div>\n</ul>\n  <blockquote>botocore.exceptions.ParamValidationError: Parameter validation failed:\nUnknown parameter in AttributeUpdates.RememberSession: &#34;pie_order&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;include_other&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;time_period_range&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;size_range&#34;, must be one of: Value, Action\n</blockquote>\n</div>\n\n<div class=\"plain\">\n    <p>\n      This is the Copy/Paste friendly version of the traceback.\n    </p>\n    <textarea cols=\"50\" rows=\"10\" name=\"code\" readonly>Traceback (most recent call last):\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 2552, in __call__\n    return self.wsgi_app(environ, start_response)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 2532, in wsgi_app\n    response = self.handle_exception(e)\n               ^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 2529, in wsgi_app\n    response = self.full_dispatch_request()\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 1825, in full_dispatch_request\n    rv = self.handle_user_exception(e)\n         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 1823, in full_dispatch_request\n    rv = self.dispatch_request()\n         ^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py&#34;, line 1799, in dispatch_request\n    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask_login/utils.py&#34;, line 290, in decorated_view\n    return current_app.ensure_sync(func)(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/dash.py&#34;, line 1265, in dispatch\n    ctx.run(\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/_callback.py&#34;, line 450, in add_context\n    output_value = func(*func_args, **func_kwargs)  # %% callback invoked %%\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/Developer/NZ-Bills/app/bills/callbacks.py&#34;, line 509, in reset_fig\n    update_usr_session_to_db(username=current_user.name, session_data=DEFAULT_VALUES)\n  File &#34;/Users/harsh/Developer/NZ-Bills/app/bills/internal.py&#34;, line 77, in update_usr_session_to_db\n    USERS_TABLE.update_item(\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/factory.py&#34;, line 580, in do_action\n    response = action(self, *args, **kwargs)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/action.py&#34;, line 88, in __call__\n    response = getattr(parent.meta.client, operation_name)(*args, **params)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py&#34;, line 535, in _api_call\n    return self._make_api_call(operation_name, kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py&#34;, line 936, in _make_api_call\n    request_dict = self._convert_to_request_dict(\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py&#34;, line 1007, in _convert_to_request_dict\n    request_dict = self._serializer.serialize_to_request(\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File &#34;/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/validate.py&#34;, line 381, in serialize_to_request\n    raise ParamValidationError(report=report.generate_report())\nbotocore.exceptions.ParamValidationError: Parameter validation failed:\nUnknown parameter in AttributeUpdates.RememberSession: &#34;pie_order&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;include_other&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;time_period_range&#34;, must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: &#34;size_range&#34;, must be one of: Value, Action\n</textarea>\n</div>\n<div class=\"explanation\">\n  The debugger caught an exception in your WSGI application.  You can now\n  look at the traceback which led to the error.  <span class=\"nojavascript\">\n  If you enable JavaScript you can also use additional features such as code\n  execution (if the evalex feature is enabled), automatic pasting of the\n  exceptions and much more.</span>\n</div>\n      <div class=\"footer\">\n        Brought to you by <strong class=\"arthur\">DON'T PANIC</strong>, your\n        friendly Werkzeug powered traceback interpreter.\n      </div>\n    </div>\n\n    <div class=\"pin-prompt\">\n      <div class=\"inner\">\n        <h3>Console Locked</h3>\n        <p>\n          The console is locked and needs to be unlocked by entering the PIN.\n          You can find the PIN printed out on the standard output of your\n          shell that runs the server.\n        <form>\n          <p>PIN:\n            <input type=text name=pin size=14>\n            <input type=submit name=btn value=\"Confirm Pin\">\n        </form>\n      </div>\n    </div>\n  </body>\n</html>\n\n<!--\n\nTraceback (most recent call last):\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 2552, in __call__\n    return self.wsgi_app(environ, start_response)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 2532, in wsgi_app\n    response = self.handle_exception(e)\n               ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 2529, in wsgi_app\n    response = self.full_dispatch_request()\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 1825, in full_dispatch_request\n    rv = self.handle_user_exception(e)\n         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 1823, in full_dispatch_request\n    rv = self.dispatch_request()\n         ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask/app.py\", line 1799, in dispatch_request\n    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/flask_login/utils.py\", line 290, in decorated_view\n    return current_app.ensure_sync(func)(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/dash.py\", line 1265, in dispatch\n    ctx.run(\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/dash/_callback.py\", line 450, in add_context\n    output_value = func(*func_args, **func_kwargs)  # %% callback invoked %%\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/Developer/NZ-Bills/app/bills/callbacks.py\", line 509, in reset_fig\n    update_usr_session_to_db(username=current_user.name, session_data=DEFAULT_VALUES)\n  File \"/Users/harsh/Developer/NZ-Bills/app/bills/internal.py\", line 77, in update_usr_session_to_db\n    USERS_TABLE.update_item(\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/factory.py\", line 580, in do_action\n    response = action(self, *args, **kwargs)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/boto3/resources/action.py\", line 88, in __call__\n    response = getattr(parent.meta.client, operation_name)(*args, **params)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\", line 535, in _api_call\n    return self._make_api_call(operation_name, kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\", line 936, in _make_api_call\n    request_dict = self._convert_to_request_dict(\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/client.py\", line 1007, in _convert_to_request_dict\n    request_dict = self._serializer.serialize_to_request(\n                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/harsh/.pyenv/versions/3.11.3/lib/python3.11/site-packages/botocore/validate.py\", line 381, in serialize_to_request\n    raise ParamValidationError(report=report.generate_report())\nbotocore.exceptions.ParamValidationError: Parameter validation failed:\nUnknown parameter in AttributeUpdates.RememberSession: \"pie_order\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"include_other\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"time_period_range\", must be one of: Value, Action\nUnknown parameter in AttributeUpdates.RememberSession: \"size_range\", must be one of: Value, Action\n\n\n-->\n"
if __name__ == '__main__':
    import dash
    dash_app = dash.Dash(__name__, requests_pathname_prefix='/')
    dash_app.config.suppress_callback_exceptions = True
    bills_register_dash_components(dash_app)
    dash_app.run_server(debug=True)
