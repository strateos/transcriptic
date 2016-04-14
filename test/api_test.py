import unittest
from .mockAPI import mockRoute, MockResponse, _req_call as mockCall
from .helper import load_protocol
from transcriptic import api
from transcriptic.config import Connection, AnalysisException



api._req_call = mockCall

test_ctx = Connection(email="mock@api.com", organization_id="mock", api_root="mock-api")

invalid_transfer_protocol = load_protocol('invalidTransfer')
invalid_transfer_response = load_protocol('invalidTransfer_response')
single_transfer_protocol = load_protocol('singleTransfer')
single_transfer_response = load_protocol('singleTransfer_response')


class AnalyzeTestCase(unittest.TestCase):
    def testDefaultResponses(self):
        # Setup default parameters
        route = test_ctx.get_route('analyze_run')
        call = 'post'
        # Mocks
        mock404 = MockResponse(status_code=404, text='404')
        mock400 = MockResponse(status_code=400, text='400')
        mock422 = MockResponse(status_code=422, json=invalid_transfer_response)
        mock200 = MockResponse(status_code=200, json=single_transfer_response)

        mockRoute(call, route, mock404, max_calls=1)
        with self.assertRaises(Exception):
            test_ctx.analyze_run(invalid_transfer_protocol)

        mockRoute(call, route, mock400, max_calls=1)
        with self.assertRaises(Exception):
            test_ctx.analyze_run(invalid_transfer_protocol)

        mockRoute(call, route, mock422, max_calls=1)
        with self.assertRaises(AnalysisException):
            test_ctx.analyze_run(invalid_transfer_protocol)

        mockRoute(call, route, mock200, max_calls=1)
        self.assertEqual(test_ctx.analyze_run(single_transfer_protocol), single_transfer_response)
