import requests


def _call(method, route, use_ctx=True, **kwargs):
    """Base function for handling all requests"""
    # Always use the latest connection context
    if use_ctx:
        from transcriptic import ctx
        if not ctx:
            raise Exception("No transcriptic.config.Connection context found!")
        if ctx.verbose:
            print ("{0}: {1}".format(method.upper(), route))
        if 'headers' not in kwargs:
            return getattr(requests, method)(route, headers=ctx.headers, **kwargs)
        else:
            return getattr(requests, method)(route, **kwargs)
    else:
        return getattr(requests, method)(route, **kwargs)


def get(route, **kwargs):
    return _call('get', route, **kwargs)


def put(route, **kwargs):
    return _call('put', route, **kwargs)


def post(route, **kwargs):
    return _call('post', route, **kwargs)


def delete(route, **kwargs):
    return _call('delete', route, **kwargs)

