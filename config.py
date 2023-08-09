import os

import boto3
import yaml


# def get_sqlite_uri():
#     basedir = os.path.abspath(os.path.dirname(__file__))
#     db_name = os.environ['DATABASE_URL'].split('/')[-1]
#     return f'sqlite:///{basedir}/{db_name}'


CONFIG_PATH: str = os.path.join(os.path.abspath(os.path.dirname(__file__)), "./config.yml")


with open(CONFIG_PATH, 'r') as stream:
    CONFIG_DATA = yaml.safe_load(stream)


def get_dyn_db_conn():
    return boto3.resource('dynamodb', **CONFIG_DATA['DynamoDB']['Credentials'])


class BaseConfig:
    DYN_DB_CONN = get_dyn_db_conn()
    USERS_TABLE = DYN_DB_CONN.Table(CONFIG_DATA.get('DynamoDB', {}).get('UsersTableName', 'Users'))
    NZ_PM_TABLE = DYN_DB_CONN.Table(CONFIG_DATA.get('DynamoDB', {}).get('NzPmTableName', 'NzPm'))
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'Su93rS3cr3tF1@$kK3y'  # TODO: move to config file
    PEPPER_VAL = CONFIG_DATA.get('Pepper', 'None')
    DISABLE_SIGNUP = CONFIG_DATA.get('DisableSignUp', False)
    STS_CLIENT = boto3.client('sesv2', **CONFIG_DATA['STS']['Credentials'])
    EMAIL_CONTENT = CONFIG_DATA['STS']['EmailContent']
