import os, sys, json
from os import path
import yaml
import boto3

cur_dir = path.dirname(path.realpath(__file__))
root = path.join(cur_dir, '..')
sys.path.append(path.join(root, 'orders'))

def create_db(prop_name, table_name, cf):
    allowed_ddb_props = (
        'AttributeDefinitions',
        'GlobalSecondaryIndexes',
        'BillingMode',
        'KeySchema')
    definitions = {
        k: v for k, v in
        cf['Resources'][prop_name]['Properties'].items()
        if k in allowed_ddb_props}
    definitions['TableName'] = table_name
    endpoint_url = os.environ.get('DB_ENDPOINT_URL') or None
    ddb = boto3.client('dynamodb', endpoint_url=endpoint_url)
    try:
        ddb.create_table(**definitions)
    except ddb.exceptions.ResourceInUseException:
        print(f'WARN: {table_name} already exists - will not update it!')
    ddb.get_waiter('table_exists').wait(TableName=table_name)


with open(path.join(root, 'env.json')) as c:
    os.environ.update(json.load(c)['Parameters'])


with open(path.join(root, 'template.yaml')) as cf:
    loader = yaml.SafeLoader
    # ignore unknown operations, such as !FindInMap
    yaml.add_multi_constructor('!', lambda loader, suffix, node: None, Loader=loader)
    CF = yaml.load(cf, Loader=loader)

create_db('OrdersTable', os.environ['DB_ORDERS_TABLE'], CF)
