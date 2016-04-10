import requests


def _call(method, route, **kwargs):
    """Base function for handling all requests"""
    # Always use the latest connection context
    from transcriptic import ctx
    if not ctx:
        raise Exception("No transcriptic.config.Connection context found!")
    if ctx.verbose:
        print ("{0}: {1}".format(method.upper(), route))
    return getattr(requests, method)(route, headers=ctx.headers, **kwargs)


def get(route, **kwargs):
    return _call('get', route, **kwargs)


def put(route, **kwargs):
    return _call('put', route, **kwargs)


def post(route, **kwargs):
    return _call('post', route, **kwargs)


def delete(route, **kwargs):
    return _call('delete', route, **kwargs)

