import os
from datetime import datetime
from decimal import Decimal
import simplejson
import db


def order_expiration_min():
    return os.environ.get('ORDER_EXPIRATION_MIN', 60)


def order_until_active_min():
    return os.environ.get('ORDER_UNTIL_ACTIVE_MIN', 25)


def expect_json(func):
    error = {'error': 'invalid_json'}
    def wrapper(event, *args, **kwargs):
        if event['body'] is None:
            return resp(event, error, 400)
        try:
            event['body'] = simplejson.loads(event['body'], parse_float=Decimal)
        except simplejson.JSONDecodeError:
            return resp(event, error, 400)
        return func(event, *args, **kwargs)
    return wrapper


def resp(event, body=None, code=200):
    headers = {'content-type': 'application/json'}
    response = {'statusCode': code, 'headers': headers}
    if body is not None:
        response['body'] = simplejson.dumps(body)
    return response


def dt_fromisoformat(date):
    """
    Python's datetime does not support Z at the end.
    We could use a better library for that, but what for?

    >>> dt_fromisoformat('2021-01-01')
    datetime.datetime(2021, 1, 1, 0, 0)

    >>> dt_fromisoformat('2021-01-01T00:00:00+00:00')
    datetime.datetime(2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)

    >>> dt_fromisoformat('2021-01-01T00:00:00Z')
    datetime.datetime(2021, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
    """
    if date[-1] == 'Z':
        date = date[:-1] + '+00:00'
    return datetime.fromisoformat(date)
