from datetime import datetime, timedelta, timezone
import uuid, json
from decimal import Decimal
import simplejson
import pytest
from orders import app, utils, db


def test_json_validation():
    event = base_event()
    event['body'] = '{"broken"!'
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'invalid_json'} == json.loads(ret["body"])


def test_order_count_validation():
    event = base_event(valid_order(orderCount=42))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'invalid_order_count'} == json.loads(ret["body"])


def test_order_total_validation():
    event = base_event(valid_order(orderTotal=42))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'invalid_order_total'} == json.loads(ret["body"])


def test_pickup_time_validation():
    event = base_event(valid_order(pickupTime='broken'))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'invalid_pickup_time'} == json.loads(ret["body"])

    event = base_event(valid_order(
        pickupTime=datetime.now().isoformat()))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'pickup_time_not_utc'} == json.loads(ret["body"])
    
    event = base_event(valid_order(
        pickupTime=past(seconds=10).isoformat()))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'pickup_time_in_past'} == json.loads(ret["body"])

    event = base_event(valid_order(
        orderType='SCHEDULED',
        pickupTime=future(days=3, hours=1).isoformat()))
    ret = app.create_order_handler(event, "")
    assert ret["statusCode"] == 400
    assert {'error': 'pickup_time_too_far_in_future'} == json.loads(ret["body"])


def test_order_structure_validation():
    valid = valid_order()

    ret = app.create_order_handler(base_event(valid.copy().pop('orderItems')), "")
    assert ret["statusCode"] == 400
    assert 'invalid_order_format' == json.loads(ret["body"])['error']

    ret = app.create_order_handler(base_event(valid.copy().pop('orderCount')), "")
    assert ret["statusCode"] == 400
    assert 'invalid_order_format' == json.loads(ret["body"])['error']

    ret = app.create_order_handler(base_event(valid_order(orderItems=[])), "")
    assert ret["statusCode"] == 400
    assert 'invalid_order_format' == json.loads(ret["body"])['error']


def test_base_workflow():
    active = valid_order()
    ret = app.create_order_handler(base_event(body=active), "")
    assert ret["statusCode"] == 201
    assert drop_type(active) == json.loads(ret["body"])

    scheduled_active = valid_order(
        orderType='SCHEDULED',
        pickupTime=future(minutes=5).isoformat())
    ret = app.create_order_handler(base_event(body=scheduled_active), "")
    assert ret["statusCode"] == 201
    assert drop_type(scheduled_active) == json.loads(ret["body"])

    scheduled_inactive = valid_order(
        orderType='SCHEDULED',
        pickupTime=future(days=2, hours=23).isoformat())
    ret = app.create_order_handler(base_event(body=scheduled_inactive), "")
    assert ret["statusCode"] == 201
    assert drop_type(scheduled_inactive) == json.loads(ret["body"])

    conflicting = dict(active, **{
        'orderType': 'SCHEDULED',
        'pickupTime': future(hours=1).isoformat()})
    ret = app.create_order_handler(base_event(body=conflicting), "")
    assert ret["statusCode"] == 409
    assert {'error': 'already_exists'} == json.loads(ret["body"])

    expired = db.create_order(drop_type(fix_decimals(valid_order(
        orderType='SCHEDULED',
        pickupTime=past(hours=2).isoformat()))))
    
    ret = app.list_active_orders_handler(base_event(), '')
    result = json.loads(ret['body'])
    assert ret["statusCode"] == 200
    assert 'updatedAt' in result
    assert drop_type(active) in result['orders']
    assert drop_type(scheduled_active) in result['orders']
    assert drop_type(scheduled_inactive) not in result['orders']
    assert drop_type(conflicting) not in result['orders']
    assert expired['orderId'] not in [o['orderId'] for o in result['orders']]
    
    pickup_times = [parse_dt(o) for o in result['orders']]
    assert pickup_times == sorted(pickup_times)


# utils

def fix_decimals(data):
    return simplejson.loads(simplejson.dumps(data), parse_float=Decimal)


def drop_type(order):
    order = order.copy()
    del order['orderType']
    return order


def past(**kwargs):
    return datetime.now(timezone.utc) - timedelta(**kwargs)


def future(**kwargs):
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def parse_dt(order):
    return int(utils.dt_fromisoformat(order['pickupTime']).timestamp())


def base_event(body=''):
    return {
        "body": json.dumps(body),
        "resource": "/{proxy+}",
        "queryStringParameters": {},
        "headers": {},
        "httpMethod": "POST",
        "path": "/orders/*",
    }


def valid_order(**kwargs):
    return dict({
        "orderId": str(uuid.uuid4()), # (uuid4 indicating order id)
        "orderTotal": 10.45, # (total price)
        "orderCount": 3, # (indicating the number of items in an order0 
        "orderType": "CURRENT", # (indicating the type of order: CURRENT or SCHEDULED)
        "pickupTime": datetime.now(timezone.utc).isoformat(), # (indicating UTC time of order)
        "orderItems": [
            {
                "name": "Pasta",
                "price": 5,
                "quantity": 2
            },
            {
                "name": "Cookie",
                "price": 0.23,
                "quantity": 1
            },
            {
                "name": "Gum",
                "price": 0.22,
                "quantity": 1
            }
        ]
    }, **kwargs)
