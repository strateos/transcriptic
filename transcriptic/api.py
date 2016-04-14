from __future__ import print_function
from builtins import str
import requests


def _req_call(method, route, **kwargs):
    return getattr(requests, method)(route, **kwargs)


def _call(method, route, use_ctx=True, status_response={}, merge_status=True, **kwargs):
    """Base function for handling all requests"""
    # Always use the latest connection context
    if use_ctx:
        from transcriptic import ctx
        if not ctx:
            raise Exception("No transcriptic.config.Connection context found!")
        if ctx.verbose:
            print ("{0}: {1}".format(method.upper(), route))
        if 'headers' not in kwargs:
            return _handle_response(_req_call(method, route, headers=ctx.headers, **kwargs),
                                    merge_status=merge_status, **status_response)
        else:
            return _handle_response(_req_call(method, route, **kwargs), merge_status=merge_status,
                                    **status_response)
    else:
        return _handle_response(_req_call(method, route, **kwargs), merge_status=merge_status,
                                **status_response)


def get(route, **kwargs):
    return _call('get', route, **kwargs)


def put(route, **kwargs):
    return _call('put', route, **kwargs)


def post(route, **kwargs):
    return _call('post', route, **kwargs)


def delete(route, **kwargs):
    return _call('delete', route, **kwargs)


def _handle_response(response, **kwargs):
    default_status_response = {'200': lambda resp: resp.json(),
                               '201': lambda resp: resp.json(),
                               'default': lambda resp: Exception("[%d] %s" % (resp.status_code, resp.text))
                               }
    if kwargs['merge_status']:
        kwargs.pop('merge_status')
        status_response = dict(default_status_response, **kwargs)
    else:
        kwargs.pop('merge_status')
        status_response = dict(**kwargs)
    return_val = status_response.get(str(response.status_code), default_status_response['default'])

    if isinstance(return_val(response), Exception):
        raise return_val(response)
    else:
        return return_val(response)
