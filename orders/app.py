from datetime import datetime, timedelta, timezone
import boto3, jsonschema
import db, utils


@utils.expect_json
def create_order_handler(event, _context):
    error = validate_order(event['body'])
    if error:
        return utils.resp(event, error, 400)
    order = event['body']
    # I assume that's required just for the pickup time validation
    del order['orderType']
    try:
        order = db.create_order(order)
    except db.Conflict:
        return utils.resp(
            event, {'error': 'already_exists'}, 409)
    return utils.resp(event, order, 201)


def list_active_orders_handler(event, _context):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=utils.order_expiration_min())
    end = now + timedelta(minutes=utils.order_until_active_min())
    # FIXME: only for SCHEDULED?
    orders = db.list_active_orders(start, end)
    result = {
        'updatedAt': now.isoformat(),
        'orders': orders,
    }
    return utils.resp(event, result)


def validate_order(order):
    try:
        jsonschema.validate(order, order_schema(), format_checker=jsonschema.FormatChecker())
    except jsonschema.exceptions.ValidationError as e:
        # TODO: jsonschema validation messages are hard to understand, imporve that
        return {'error': 'invalid_order_format', 'details': e.message}
    if order['orderCount'] != len(order['orderItems']):
        return {'error': 'invalid_order_count'}
    real_order_total = sum([i['price'] * i['quantity'] for i in order['orderItems']])
    if real_order_total != order['orderTotal']:
        return {'error': 'invalid_order_total'}
    try:
        pickup_dt = utils.dt_fromisoformat(order['pickupTime'])
    except ValueError:
        return {'error': 'invalid_pickup_time'}
    else:
        if not pickup_dt.tzinfo or pickup_dt.tzinfo != timezone.utc:
            return {'error': 'pickup_time_not_utc'}
        now = datetime.now(timezone.utc)
        if (now - pickup_dt).total_seconds() > 5: # allow 5 second lag to void time sync issues
            return {'error': 'pickup_time_in_past'}
        if  (pickup_dt - now) > timedelta(days=3):
            return {'error': 'pickup_time_too_far_in_future'}
        if (pickup_dt - now) > timedelta(days=3):
            return {'error': 'pickup_time_too_far_in_future'}


# TODO: move it to the API Gateway openapi spec and reuse
def order_schema():
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'orderId': {'type': 'string', 'minLength': 1},
            'orderTotal': {'type': 'number', 'minimum': 0},
            'orderCount': {'type': 'integer', 'minimum': 1},
            'orderType': {'type': 'string', 'enum': ['SCHEDULED', 'CURRENT']},
            # honestly, I do not trust jsonschema's datetime validation 
            'pickupTime': {'type': 'string', 'format': 'date-time'},
            'orderItems': {
                'type': 'array',
                'minItems': 1,
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        # TODO: load that dynamically from the customer's menu
                        'name': {'type': 'string', 'minLength': 1},
                        'price': {'type': 'number', 'minimum': 0},
                        'quantity': {'type': 'integer', 'mimimum': 1}
                    },
                    'required': ['name', 'price', 'quantity']
                }
            }
        },
        'required': [
            'orderId',
            'orderTotal',
            'orderCount',
            'orderType',
            'pickupTime',
            'orderItems'
        ]
    }
