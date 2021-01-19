import os
import sys

import pytest

from .helpers.mockAPI import MockResponse
from .helpers.util import load_protocol


sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))


# TODO: Migrate tests utilizing this to use the `TestConnection` pattern instead.
@pytest.fixture()
def test_api(monkeypatch):
    from transcriptic.config import Connection

    from .helpers.mockAPI import _req_call as mockCall

    api = Connection(email="mock@api.com", organization_id="mock", api_root="mock-api")
    monkeypatch.setattr(api, "_req_call", mockCall)
    return api


class JsonDB:
    """Contains dictionary of json objects used for testing purposes"""

    def __init__(self):
        self.json_db = {}

    def __getitem__(self, name):
        return self.json_db[name]

    def load(self, name=None, test_dir=None, path=None):
        self.json_db[name] = load_protocol(name, test_dir, path)

    def reset(self):
        self.json_db = {}


@pytest.fixture(scope="module")
def json_db():
    return JsonDB()


class ResponseDB:
    """
    Contains dictionary of MockResponse used for testing purposes
    TODO: Simplify this by using `@responses.activate` pattern
    """

    def __init__(self):
        self.mock_responses = {}

    def __getitem__(self, name):
        return self.mock_responses[name]

    def load(self, name, status_code=None, json=None, text=None):
        self.mock_responses[name] = MockResponse(status_code, json, text)

    def reset(self):
        self.mock_responses = {}


@pytest.fixture(scope="module")
def response_db():
    return ResponseDB()


@pytest.fixture(scope="module")
def test_connection():
    from transcriptic.config import Connection

    return Connection(
        email="mock@api.com", organization_id="mock", api_root="http://mock-api"
    )
