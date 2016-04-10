from requests import Response

"""Keys in mockDB correspond to (method, route) calls"""
mockDB = dict()


class MockResponse(Response):
    """Mocks requests.Response"""

    def __init__(self, status_code=None, json=None):
        self.status_code = status_code
        self.json = json

    def status_code(self):
        return self.status_code

    def json(self):
        return self.json


def _call(method, route, **kwargs):
    if (method, route) in mockDB:
        return mockDB[(method, route)]
    else:
        raise RuntimeError("Method: {method} and Route: {route} needs to be mocked.".format(**locals()))


def mockRoute(method, route, response):
    if not isinstance(response, MockResponse):
        raise TypeError("Response needs to be a MockResponse object.")
    mockDB[(method, route)] = response
