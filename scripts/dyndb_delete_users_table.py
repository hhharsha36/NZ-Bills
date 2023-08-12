from datetime import datetime

import boto3


DYNAMO_DB_CONF = dict(endpoint_url='http://localhost:8000')
TABLE_NAME = 'Users'


def delete_users_table(dynamodb):
    dynamodb = boto3.resource('dynamodb', **dynamodb)
    users_table = dynamodb.Table(TABLE_NAME)
    users_table.delete()
    users_table.wait_until_not_exists()


if __name__ == '__main__':
    # book_table = create_pm_table(DYNAMO_DB_CONF)
    # print("Status:", book_table.table_status)
    # print(f'{book_table=}')
    # insert_pm_data(DYNAMO_DB_CONF)
    delete_users_table(DYNAMO_DB_CONF)
