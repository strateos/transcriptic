import json

import requests

from transcriptic.cli import cli

from ..helpers.fixtures import *
from ..helpers.mockAPI import MockResponse


# Structure of the response object from SCLE
def queue_test_success_res(sessionId="testSessionId"):
    return {"success": True, "sessionId": sessionId}


def app_config_res():
    return {"hostManifest": {"lab": {"workcell": "something.bar.foo"}}}


def mock_api_endpoint():
    return "foo.bar.baz/lab/workcell"


def mockget(*args, **kwargs):
    return MockResponse(0, app_config_res(), json.dumps(app_config_res()))


@pytest.fixture
def ap_file(tmpdir_factory):
    """Make a temp autoprotocol file"""
    path = tmpdir_factory.mktemp("foo").join("ap.json")
    with open(str(path), "w") as f:
        f.write("{}")  # any valid json works
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
    assert result.exit_code == 0
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
    assert result.exit_code == 0
    assert "Error: --workcell-id, --session-id are mutually exclusive." in result.stderr
