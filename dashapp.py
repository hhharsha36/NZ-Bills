# https://hackersandslackers.com/plotly-dash-with-flask/

import logging

from app import create_app
from config import BaseConfig

server = create_app()


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
if BaseConfig.DEBUG_MODE:
    logging.getLogger().setLevel(logging.DEBUG)


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=5001, debug=BaseConfig.DEBUG_MODE)
