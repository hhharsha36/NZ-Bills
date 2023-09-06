import os
from pprint import pprint

import boto3
import yaml

CONFIG_PATH: str = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../config.yml")

with open(CONFIG_PATH, 'r') as stream:
    CONFIG_DATA = yaml.safe_load(stream)
DYNAMO_DB_CONF = CONFIG_DATA['DynamoDB']['Credentials']


def create_books_table(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    table = dynamodb.create_table(
        TableName='Users',
        KeySchema=[
            # {
            #     'AttributeName': '_id',
            #     'KeyType': 'RANGE'  # Partition key
            # },
            {
                'AttributeName': 'Username',
                'KeyType': 'HASH'
            },
            # {
            #     'AttributeName': 'title',
            #     'KeyType': 'RANGE'  # Sort key
            # }
        ],
        AttributeDefinitions=[
            # {
            #     'AttributeName': '_id',
            #     # AttributeType refers to the data type 'N' for number type and 'S' stands for string type.
            #     'AttributeType': 'S'
            # },
            {
                'AttributeName': 'Username',
                'AttributeType': 'S'
            },
            # {
            #     'AttributeName': 'Password',
            #     'AttributeType': 'S'
            # },
            # {
            #     'AttributeName': 'CreatedAt',
            #     'AttributeType': 'S'
            # },
            # {
            #     'AttributeName': 'UpdatedAt',
            #     'AttributeType': 'S'
            # },
            # {
            #     'AttributeName': 'pie_order',
            #     'AttributeType': 'S'
            # },
            # {
            #     'AttributeName': 'include_other',
            #     'AttributeType': 'S'
            # },
            # {
            #     'AttributeName': 'n_clicks',
            #     'AttributeType': 'N'
            # },
            # {
            #     'AttributeName': 'time_period_range',
            #     'AttributeType': 'N'
            # },
            # {
            #     'AttributeName': 'size_range',
            #     'AttributeType': 'N'
            # },
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={
            # ReadCapacityUnits set to 10 strongly consistent reads per second
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10  # WriteCapacityUnits set to 10 writes per second
        }
    )
    return table


def read_all(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    pm_table = dynamodb.Table('Users')
    response = pm_table.scan()
    print(f'{response=}')
    if not isinstance(response, dict) or not response.get('Items'):
        ValueError('unable to retrieve pm information from DB')
    for r in response['Items']:
        pprint(f'{r=}')


if __name__ == '__main__':
    users_table = create_books_table(DYNAMO_DB_CONF)
    # print("Status:", users_table.table_status)
    # print(f'{users_table=}')
    read_all(DYNAMO_DB_CONF)
