import boto3


DYNAMO_DB_CONF = dict(endpoint_url='http://localhost:8000')


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


if __name__ == '__main__':
    book_table = create_books_table(DYNAMO_DB_CONF)
    print("Status:", book_table.table_status)
    print(f'{book_table=}')
