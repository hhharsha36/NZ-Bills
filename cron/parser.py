import json
# from urllib import request, parse

from package import requests


def lambda_handler(event, context):
    with open('./config.json') as f:
        config = json.load(f)
        print(config)

    res = requests.post(config.get('url'), json={'key': config.get('key')})
    print(res.status_code)
    print(res.json())
    return res


if __name__ == '__main__':
    lambda_handler(None, None)
