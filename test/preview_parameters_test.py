
import json
import os

import pytest

from transcriptic.preview_parameters import PreviewParameters
from transcriptic import Connection

@pytest.fixture(scope='module')
def api():
    api = Connection.from_file('~/.transcriptic')

@pytest.fixture(params=[('inputs_time_series', 'preview_parameters_time_series.json')])
def test_time_series_preview_parameters(request, api):
    # Open input quick launch parameters
    input_params = None
    test_path = os.getcwd() + '/resources/{}'.format(request.params[0])
    with open(test_path, 'r') as f:
        input_params = json.loads(f.read())
    pp = PreviewParameters(input_params)
    pp.preview