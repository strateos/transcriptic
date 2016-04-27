import pytest

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))

from util import load_protocol


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


@pytest.fixture()
def mock_api_call(monkeypatch):
    """Monkey patches normal api call to use mock call. Use this fixture when you need to mock a connection"""
    from transcriptic import api
    from mockAPI import _req_call as mockCall
    monkeypatch.setattr(api, '_req_call', mockCall)


from mockAPI import MockResponse


class ResponseDB:
    """Contains dictionary of MockResponse used for testing purposes"""

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
