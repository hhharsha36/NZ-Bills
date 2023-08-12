import os.path

import dash
from flask import Flask
from flask.helpers import get_root_path
from flask_login import login_required
import logging

from config import BaseConfig

# TODO: remove before deployment
# from app import dashapp1 as test_app
from app.dashapp1.layout import layout as a1_layout
from app.dashapp1.callbacks import register_callbacks as a1_register_callbacks
from app.webapp import server_bp, SignIn, get_user_from_db

from app.bills.callbacks import bills_register_dash_components


def create_app():
    server = Flask(__name__)
    server.config.from_object(BaseConfig)

    register_dash_apps(server)
    register_extensions(server)
    register_blueprints(server)

    logging.debug(f'{print(server.url_map)=}')  # TODO: remove

    return server


def register_dash_apps(app):
    # Meta tags for viewport responsiveness
    meta_viewport = {
        "name": "viewport",
        "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

    # TODO: remove `dashapp1`
    # dashapp1 = dash.Dash(__name__,
    #                      server=app,
    #                      url_base_pathname='/dashboard/',
    #                      assets_folder=get_root_path(__name__) + '/dashboard/assets/',
    #                      meta_tags=[meta_viewport])
    # with app.app_context():
    #     dashapp1.title = 'Dashapp 1'
    #     dashapp1.layout = a1_layout
    #     a1_register_callbacks(dashapp1)
    #
    # _protect_dash_views(dashapp1)

    bills_assets_path = os.path.join(get_root_path(__name__), 'bills', 'assets')
    # TODO: remove
    print(f'{bills_assets_path=}')
    logging.debug(f'{bills_assets_path=}')
    bills_app = dash.Dash(__name__,
                          server=app,
                          url_base_pathname='/bills/',
                          assets_folder=bills_assets_path,
                          meta_tags=[meta_viewport],
                          prevent_initial_callbacks="initial_duplicate")
    with app.app_context():
        # dashapp1.title = 'New Zealand Parliament Bills Visualisation'
        # dashapp1.layout =
        bills_register_dash_components(bills_app)

    _protect_dash_views(bills_app)


def _protect_dash_views(dashapp):
    for view_func in dashapp.server.view_functions:
        if view_func.startswith(dashapp.config.url_base_pathname):
            dashapp.server.view_functions[view_func] = login_required(
                dashapp.server.view_functions[view_func])


def load_user_from_db(username: str):
    u = get_user_from_db(username=username)
    # u = users_table.find_one({"Username": username.upper()})  # TODO: update query
    if not u:
        return None
    # return SignIn(username=username, password='None', user_col=users_collection)
    sign_in_obj = SignIn(username=u['Username'], password=u['Password'])
    return sign_in_obj


def register_extensions(server):
    from app.extensions import db, login_manager

    # db.init_app(server)
    login_manager.init_app(server)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        logging.debug(f'user_loader called')
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return load_user_from_db(user_id)

    # migrate.init_app(server, db)


def register_blueprints(server):
    server.register_blueprint(server_bp)
