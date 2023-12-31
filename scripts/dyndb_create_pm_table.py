from datetime import datetime
import logging
from time import sleep
import os

import boto3
import yaml


CONFIG_PATH: str = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../config.yml")

with open(CONFIG_PATH, 'r') as stream:
    CONFIG_DATA = yaml.safe_load(stream)
DYNAMO_DB_CONF = CONFIG_DATA['DynamoDB']['Credentials']
TABLE_NAME = 'NzPm'


PM_LIST = [
    {
        'name': 'Chris Hipkins',
        'colour': 'Maroon',
        'term': datetime(2024, 1, 25).timestamp(),
        'party': 'Labour Party'
    },
    {
        'name': 'Jacinda Ardern',
        'colour': 'Red',
        'term': datetime(2023, 1, 24).timestamp(),
        'party': 'Labour Party'
    },
    {
        'name': 'Bill English',
        'colour': 'RoyalBlue',
        'term': datetime(2017, 11, 26).timestamp(),
        'party': 'National Party'
    },
    {
        'name': 'John Key',
        'colour': 'MediumSlateBlue',
        'term': datetime(2016, 12, 12).timestamp(),
        'party': 'National Party'
    },
    {
        'name': 'Helen Clark',
        'colour': 'Tomato',
        'term': datetime(2008, 11, 19).timestamp(),
        'party': 'Labour Party'
    },
]


def create_pm_table(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {
                'AttributeName': 'name',
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'name',
                'AttributeType': 'S'
            }
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={
            # ReadCapacityUnits set to 10 strongly consistent reads per second
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10  # WriteCapacityUnits set to 10 writes per second
        }
    )
    return table


def insert_pm_data(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    tmp_pm_table = dynamodb.Table(TABLE_NAME)
    logging.debug(f'{tmp_pm_table.scan()=}')
    for pm_details in PM_LIST:
        pm_details['term'] = int(pm_details['term'])
        response = tmp_pm_table.put_item(Item=pm_details)
        logging.debug(f'{response=}')
    return None


def read_all(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    tmp_pm_table = dynamodb.Table(TABLE_NAME)
    response = tmp_pm_table.scan()
    logging.debug(f'{response=}')
    if not isinstance(response, dict) or not response.get('Items'):
        ValueError('unable to retrieve pm information from DB')
    for r in response['Items']:
        logging.debug(f'{r=}')
        r['term'] = int(r['term'])
    response = sorted(response['Items'], key=lambda x: x.get('term'), reverse=True)
    logging.debug(f'sorted {response=}')


if __name__ == '__main__':
    pm_table = create_pm_table(DYNAMO_DB_CONF)
    logging.debug("Status:", pm_table.table_status)
    logging.debug(f'{pm_table=}')
    logging.debug('sleeping for 10 seconds')
    sleep(10)
    insert_pm_data(DYNAMO_DB_CONF)
    read_all(DYNAMO_DB_CONF)
