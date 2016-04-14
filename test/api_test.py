import unittest
from .mockAPI import mockRoute, MockResponse, _req_call as mockCall
from transcriptic import routes
import json

from transcriptic import api
from transcriptic.config import Connection
api._req_call = mockCall

api_root = "https://secure.transcriptic.com"
org_id = "transcriptic"
email = "test@transcriptic.com"
ctx = Connection(email=email, organization_id=org_id, api_root=api_root)
sample_protocol = json.loads(open('test/json/simpleWorkingAP.json').read())


class AnalyzeTestCase(unittest.TestCase):
    def testDefaultResponses(self):
        mock404 = MockResponse(status_code=404, text='404')
        mockRoute('post', routes.analyze_run(api_root, org_id), mock404, max_calls=1)
        with self.assertRaises(Exception):
            ctx.analyze_run(sample_protocol)

