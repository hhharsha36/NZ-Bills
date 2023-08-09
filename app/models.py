# from flask_login import UserMixin
# from werkzeug.security import check_password_hash
# from werkzeug.security import generate_password_hash
import logging

from app.extensions import users_table, login_manager
from app.webapp import SignIn, get_user_from_db


# @login.user_loader
# def load_user(id):
#     return User.query.get(int(id))


# @login_manager.user_loader
# def load_user(user_id):
#     logging.debug(f'user_loader called')
#     # since the user_id is just the primary key of our user table, use it in the query for the user
#     return load_user_from_db(user_id)
#
#
# def load_user_from_db(username: str):
#     u = get_user_from_db(username=username)
#     # u = users_table.find_one({"Username": username.upper()})  # TODO: update query
#     if not u:
#         return None
#     # return SignIn(username=username, password='None', user_col=users_collection)
#     sign_in_obj = SignIn(username=u['Username'], password=u['Password'])
#     return sign_in_obj


# class User(UserMixin, db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(64), index=True, unique=True)
#     password_hash = db.Column(db.String(128))
#
#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)
#
#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)
#
#     def __repr__(self):
#         return '<User {}>'.format(self.username)
