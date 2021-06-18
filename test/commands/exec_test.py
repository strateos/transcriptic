import json

import requests

from transcriptic.cli import cli

from ..helpers.fixtures import *
from ..helpers.mockAPI import MockResponse


# Structure of the response object from SCLE
def queue_test_success_res(sessionId="testSessionId"):
    return {"success": True, "sessionId": sessionId}

fake_valid_URL = "something.bar.foo"
def app_config_res():
    return {"hostManifest": {"lab": {"workcell": {"url": fake_valid_URL}}}}


def mock_api_endpoint():
    return "foo.bar.baz/lab/workcell"


def mockget(*args, **kwargs):
    return MockResponse(0, app_config_res(), json.dumps(app_config_res()))

@pytest.fixture
def ap_file(tmpdir_factory):
    """Make a temp autoprotocol file"""
    path = tmpdir_factory.mktemp("foo").join("ap.json")
    with open(str(path), "w") as f:
        payload = {
            "instructions": [
                {"op": "provision", "x_human": True },
                {"op": "uncover"},
                {"op": "spin"},
                {"op": "cover"}
            ]
        }
        print("Pyalod: ")
        print(json.dumps(payload))
        f.write(json.dumps(payload))
    return path



def test_unspecified_api(cli_test_runner, ap_file):
    result = cli_test_runner.invoke(cli, ["exec", str(ap_file)])
    assert result.exit_code != 0
    assert "Missing option '--api'" in result.stderr


def test_good_autoprotocol(cli_test_runner, monkeypatch, ap_file):
    def mockpost(*args, **kwargs):
        return MockResponse(
            0, queue_test_success_res(), json.dumps(queue_test_success_res())
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint()]
    )
    assert result.exit_code == 0
    assert (
        f"Success. View http://{mock_api_endpoint()}/dashboard to see the scheduling outcome."
        in result.output
    )


def test_bad_autoprotocol(cli_test_runner):
    result = cli_test_runner.invoke(
        cli, ["exec", "bad-file-handle", "-a", mock_api_endpoint()]
    )
    assert result.exit_code != 0
    assert "Invalid value for '[AUTOPROTOCOL]': Could not open file" in result.stderr


def test_bad_deviceset(cli_test_runner, ap_file):
    result = cli_test_runner.invoke(
        cli,
        [
            "exec",
            str(ap_file),
            "--device-set",
            "bad-file-handle",
            "-a",
            mock_api_endpoint(),
        ],
    )
    assert result.exit_code != 0
    assert (
        "Invalid value for '--device-set' / '-d': Could not open file: bad-file-handle:"
        in result.stderr
    )


def test_bad_api_response(cli_test_runner, monkeypatch, ap_file):
    def mockpost(*args, **kwargs):
        return MockResponse(0, "not-json", "not-json")

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint()]
    )
    assert result.exit_code != 0
    assert "Error: " in result.stderr


def test_good_workcell(cli_test_runner, monkeypatch, ap_file):
    def mockpost(*args, **kwargs):
        return MockResponse(
            0, queue_test_success_res(), json.dumps(queue_test_success_res())
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint(), "-w", "wc3"]
    )
    assert result.exit_code == 0
    assert (
        f"Success. View http://{mock_api_endpoint()}/dashboard to see the scheduling outcome."
        in result.output
    )


def test_bad_workcell(cli_test_runner, monkeypatch, ap_file):
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint(), "-w", "hello.world"]
    )
    assert result.exit_code != 0
    assert "Error: " in result.stderr


def test_session_id(cli_test_runner, monkeypatch, ap_file):
    sessionId = "hi_there"

    def mockpost(*args, **kwargs):
        return MockResponse(
            0,
            queue_test_success_res(sessionId),
            json.dumps(queue_test_success_res(sessionId)),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        [
            "exec",
            str(ap_file),
            "-a",
            mock_api_endpoint(),
            "-s",
            sessionId,
        ],
    )
    assert result.exit_code == 0
    assert (
        f"Success. View http://{mock_api_endpoint()}/dashboard to see the scheduling outcome."
        in result.output
    )


def test_too_many_workcell_definition_arguments(cli_test_runner, monkeypatch, ap_file):

    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-s", "anthing", "-w", "wc0"],
    )
    assert result.exit_code != 0
    assert "Error: --workcell-id, --session-id are mutually exclusive." in result.stderr



def test_invalid_filters(cli_test_runner, monkeypatch, ap_file):
    invalid_command = [
        "-e",
        "10",
        "-i",
        "10",
        "-e",
        "2-1",
        "-i",
        "3-6",
        "-e",
        "anything",
    ]
    invalid_filters = set(filter(lambda v: not v.startswith("-"), invalid_command))
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint()]
        + invalid_command,
    )
    assert result.exit_code != 0
    assert "Error: invalid filters" in result.stderr
    assert "(number of instructions: 4)" in result.stderr
    for inv in invalid_filters:
        assert inv in result.stderr

def test_filter_instruction_type(cli_test_runner, monkeypatch, ap_file):
    payloads= {}
    def mockpost(*args, **kwargs):
        payloads[args] = kwargs
        return MockResponse(
            0,
            queue_test_success_res(),
            json.dumps(queue_test_success_res()),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-e", "type:provision" ]
    )
    assert result.exit_code == 0, result.stderr
    assert "Info: filter type:provision matches instructions at indices: 0" in result.output
    key = (f'http://{fake_valid_URL}/testRun',)
    assert key in payloads
    payload_to_testRun = payloads[key]["json"]["autoprotocol"]
    assert [ instruction["op"] for instruction in payload_to_testRun["instructions"] ] == [ "uncover", "spin", "cover" ]

def test_filter_instruction_idx(cli_test_runner, monkeypatch, ap_file):
    payloads= {}
    def mockpost(*args, **kwargs):
        payloads[args] = kwargs
        return MockResponse(
            0,
            queue_test_success_res(),
            json.dumps(queue_test_success_res()),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-e", "1" ]
    )
    assert result.exit_code == 0, result.stderr
    key = (f'http://{fake_valid_URL}/testRun',)
    assert key in payloads
    payload_to_testRun = payloads[key]["json"]["autoprotocol"]
    assert [ instruction["op"] for instruction in payload_to_testRun["instructions"] ] == [ "provision", "spin", "cover" ]

def test_filter_instruction_range(cli_test_runner, monkeypatch, ap_file):
    payloads= {}
    def mockpost(*args, **kwargs):
        payloads[args] = kwargs
        return MockResponse(
            0,
            queue_test_success_res(),
            json.dumps(queue_test_success_res()),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-e", "1-2" ]
    )
    assert result.exit_code == 0, result.stderr
    key = (f'http://{fake_valid_URL}/testRun',)
    assert key in payloads
    payload_to_testRun = payloads[key]["json"]["autoprotocol"]
    assert [ instruction["op"] for instruction in payload_to_testRun["instructions"] ] == [ "provision", "cover" ]

def test_filter_instruction_range_with_include(cli_test_runner, monkeypatch, ap_file):
    payloads= {}
    def mockpost(*args, **kwargs):
        payloads[args] = kwargs
        return MockResponse(
            0,
            queue_test_success_res(),
            json.dumps(queue_test_success_res()),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-e", "1-3", "-i", "2" ]
    )
    assert result.exit_code == 0, result.stderr
    key = (f'http://{fake_valid_URL}/testRun',)
    assert key in payloads
    payload_to_testRun = payloads[key]["json"]["autoprotocol"]
    assert [ instruction["op"] for instruction in payload_to_testRun["instructions"] ] == [ "provision", "spin" ]

def test_filter_instruction_human(cli_test_runner, monkeypatch, ap_file):
    payloads= {}
    def mockpost(*args, **kwargs):
        payloads[args] = kwargs
        return MockResponse(
            0,
            queue_test_success_res(),
            json.dumps(queue_test_success_res()),
        )

    monkeypatch.setattr(requests, "post", mockpost)
    monkeypatch.setattr(requests, "get", mockget)
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "-e", "human" ]
    )
    assert result.exit_code == 0, result.stderr
    key = (f'http://{fake_valid_URL}/testRun',)
    assert "Info: filter human matches instructions at indices: 0" in result.output
    assert key in payloads
    payload_to_testRun = payloads[key]["json"]["autoprotocol"]
    assert [ instruction["op"] for instruction in payload_to_testRun["instructions"] ] == [ "uncover", "spin", "cover" ]
