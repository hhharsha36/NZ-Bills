# https://hackersandslackers.com/plotly-dash-with-flask/

import logging
from app import create_app

server = create_app()


# TODO: change log level from `DEBUG`
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=5001, debug=True)
