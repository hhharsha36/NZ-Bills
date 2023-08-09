import logging

from argon2.exceptions import VerifyMismatchError, VerificationError
from argon2 import PasswordHasher
from flask_login import LoginManager
# from flask_migrate import Migrate
# from flask_sqlalchemy import SQLAlchemy


# from app.webapp import SignIn, get_user_from_db
from config import BaseConfig


# CONFIG_PATH: str = "../config.yml"
# pepper_value: str = "None"
#
#
# def get_pepper():
#     global pepper_value
#     with open(CONFIG_PATH, 'r') as stream:
#         data_loaded = yaml.safe_load(stream)
#         if data_loaded.get('Pepper'):
#             pepper_value = str(data_loaded['Pepper'])
#     logging.info(f"successfully fetched pepper value")
#     return pepper_value


db = BaseConfig.DYN_DB_CONN  # TODO: convert to DynamoDB connection
users_table = BaseConfig.USERS_TABLE  # TODO: fill based on `db` variable

# migrate = Migrate()
login_manager = LoginManager()


class Crypt:
    def __init__(self):
        # global pepper_value
        # self._pepper = pepper_value
        self._pepper = BaseConfig.PEPPER_VAL
        self._ph = PasswordHasher()
        logging.info(f"crypt class initialised")

    def concat_pwd(self, salt: str, plain_txt_pwd: str):
        return f"{salt}${self._pepper}${plain_txt_pwd}"

    def encrypt(self, salt: str, plain_txt_pwd: str):
        logging.info(f"password with salt `{salt}` encrypted")
        return self._ph.hash(self.concat_pwd(salt=salt, plain_txt_pwd=plain_txt_pwd))

    def verify(self, hash_val: str, salt: str, plain_txt_pwd: str):
        try:
            logging.info(f"verifying user with salt `{salt}")
            return self._ph.verify(hash=hash_val, password=self.concat_pwd(salt=salt, plain_txt_pwd=plain_txt_pwd))
        except (VerificationError, VerifyMismatchError):
            logging.info(f"invalid password by user with salt `{salt}")
            return False
