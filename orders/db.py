import os
from datetime import timedelta
import boto3
from boto3.dynamodb.conditions import Attr, Key
import utils


ENDPOINT_URL = os.environ.get('DB_ENDPOINT_URL') or None


def create_order(order):
    table = orders_table()
    try:
        table.put_item(
            Item=order_to_ddb(order),
            ConditionExpression='attribute_not_exists(orderId)')
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        raise Conflict
    return order_from_ddb(order)


# TODO: should we introduce pagination?
def list_active_orders(start, end):
    start_ts = ts(start)
    end_ts = ts(end)
    hours = hours_between_dates(round_to_hour(start), round_to_hour(end))
    if len(hours) == 1:  # we can grab everything with one query
        res = do_get_active_orders(
            hours[0],
            Attr('pickupTimeTs').between(start_ts, end_ts))
    else:  # apply filtering to start/end hours and simply get everything in between
        res = do_get_active_orders(hours[0], Attr('pickupTimeTs').gte(start_ts))
        for h in hours[1:-1]: res += do_get_active_orders(h)
        res += do_get_active_orders(hours[-1], Attr('pickupTimeTs').lte(end_ts))
    return [order_from_ddb(o) for o in res]


def do_get_active_orders(hour, filter=None):
    table = orders_table()
    params = {
        'IndexName': 'pickupHourTsPickupTimeTsOrderIdIndex',
        'KeyConditionExpression': Key('pickupHourTs').eq(ts(hour))}
    if filter: params['FilterExpression'] = filter
    result = table.query(**params)
    return result['Items']


def orders_table():
    resource = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    return resource.Table(os.environ.get('DB_ORDERS_TABLE'))


def order_to_ddb(order):
    pickup_dt = utils.dt_fromisoformat(order['pickupTime'])
    pickup_ts = ts(pickup_dt)
    order['pickupTimeTs'] = pickup_ts
    order['pickupTimeTsOrderId'] = f'{pickup_ts}:{order["orderId"]}'
    order['expirationTs'] = ts(pickup_dt + timedelta(minutes=utils.order_expiration_min()))
    order['pickupHourTs'] = ts(round_to_hour(pickup_dt))
    return order


def order_from_ddb(order):
    del order['pickupTimeTs']
    del order['pickupHourTs']
    del order['pickupTimeTsOrderId']
    del order['expirationTs']
    return order


def round_to_hour(dt):
    return dt.replace(second=0, microsecond=0, minute=0)


def ts(dt):
    return int(dt.timestamp())


def hours_between_dates(start, end):
    hours = [start]
    hour = start
    while hour < end:
        hour += timedelta(hours=1)
        hours.append(hour)
    return hours


class Conflict(Exception):
    pass
