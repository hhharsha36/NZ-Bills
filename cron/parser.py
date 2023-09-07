import json
import logging
# from urllib import request, parse

from package import requests


def lambda_handler(event, context):
    with open('./config.json') as f:
        config = json.load(f)
        logging.debug(f'{config=}')

    res = requests.post(config.get('url'), json={'key': config.get('key')})
    logging.debug(f'{res.status_code=}')
    logging.debug(f'{res.json()=}')
    return res


if __name__ == '__main__':
    lambda_handler(None, None)
