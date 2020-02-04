import json
import os
import pytest
from transcriptic.preview_parameters import PreviewParameters
from transcriptic import Connection


@pytest.fixture(scope='module')
def api():
    api = Connection.from_file('~/.transcriptic')


def test_time_series_preview_parameters(api):
    # Open input quick launch parameters
    input_params = None
    test_path = os.getcwd() + '/test/resources/mock_quick_launch_inputs.json'
    with open(test_path, 'r') as f:
        input_params = json.loads(f.read())

    # Compare preview parameters to mock preview parameters
    mock_params = None
    mock_path = os.getcwd() + '/test/resources/mock_preview_parameters.json'
    with open(mock_path) as f:
        mock_params = json.loads(f.read())

    # Instantiate PreviewParameters with quick launch inputs
    pp = PreviewParameters(input_params)

    # Comparison for pytests
    for preview, preview_dict in mock_params.items():
        # Access the 'refs' to compare container name and container properties
        pp_refs = pp.preview[preview]['refs']
        for cont_name, cont_dict in preview_dict['refs'].items():
            pp_cont = pp_refs[cont_name]
            assert(cont_dict['seal'] == pp_cont['seal'])
            assert(cont_dict['label'] == pp_cont['label'])
            assert(cont_dict['store'] == pp_cont['store'])
            assert(cont_dict['type'] == pp_cont['type'])
            aliquots = sorted([int(x) for x in cont_dict['aliquots']])
            assert(aliquots == list(pp_cont['aliquots'].keys()))

        # Access the 'parameters' to compare protocol paramerters
        pp_params = pp.preview[preview]['parameters']
        for param, param_obj in preview_dict['parameters'].items():
            pp_type_obj = pp_params[param]
            if isinstance(param_obj, dict):
                for k, v in param_obj.items():
                    assert(v == pp_type_obj[k])
            elif isinstance(param_obj, list):
                for i, elm in enumerate(param_obj):
                    assert(elm == pp_type_obj[i])
            else:
                assert(param_obj == pp_type_obj)
