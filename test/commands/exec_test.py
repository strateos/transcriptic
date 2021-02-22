import json

from datetime import datetime, timedelta

import requests

from transcriptic.cli import cli

from ..helpers.fixtures import *
from ..helpers.mockAPI import MockResponse


# Structure of the response object from SCLE
def queue_test_success_res(sessionId="testSessionId"):
    return {"success": True, "sessionId": sessionId}


def mock_api_endpoint():
    return "foo.bar.baz"


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
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint()]
    )
    assert result.exit_code == 0
    assert (
        f"Success. View {mock_api_endpoint()}/dashboard?sessionId=testSessionId to see the scheduling outcome."
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
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint(), "-w", "wc3"]
    )
    assert result.exit_code == 0
    assert (
        f"Success. View {mock_api_endpoint()}/dashboard?sessionId=testSessionId to see the scheduling outcome."
        in result.output
    )


def test_bad_workcell(cli_test_runner, ap_file):
    result = cli_test_runner.invoke(
        cli, ["exec", str(ap_file), "-a", mock_api_endpoint(), "-w", "bad-workcell-id"]
    )
    assert result.exit_code != 0
    assert "Workcell id must be like wcN but was bad-workcell-id" in result.stderr


def test_valid_relative_time(cli_test_runner, monkeypatch, ap_file):
    capture_post_payload = list()

    def mockpost(*args, **kwargs):
        capture_post_payload.append(kwargs)
        return MockResponse(
            0, queue_test_success_res(), json.dumps(queue_test_success_res())
        )

    monkeypatch.setattr(requests, "post", mockpost)
    delta = 60
    # epoch time in millis
    current_time_plusdelta = datetime.now() + timedelta(minutes=1 + delta)
    expected_time = (
        datetime(  # ignore seconds to ceil to the next minute
            current_time_plusdelta.year,
            current_time_plusdelta.month,
            current_time_plusdelta.day,
            current_time_plusdelta.hour,
            current_time_plusdelta.minute,
        ).timestamp()
        * 1000
    )
    result = cli_test_runner.invoke(
        cli,
        ["exec", str(ap_file), "-a", mock_api_endpoint(), "--schedule-delay", delta],
    )
    assert result.exit_code == 0
    assert (
        f"Success. View {mock_api_endpoint()}/dashboard?sessionId=testSessionId to see the scheduling outcome."
        in result.output
    )
    for payload in capture_post_payload:
        if "json" in payload and "scheduleAt" in payload["json"]:
            assert (
                abs(payload["json"]["scheduleAt"] - expected_time) <= 60 * 1000
            )  # allow rounding error?
            break
    else:
        assert (
            False
        ), f"No request was made with a 'scheduleAt' key. {capture_post_payload}"


def test_valid_absolute_time(cli_test_runner, monkeypatch, ap_file):
    current_time = datetime.now()
    expected_time = (
        datetime(
            current_time.year, current_time.month, current_time.day, 12, 34
        ).timestamp()
        * 1000
    )
    time_to_parse = "12:34"
    for extra in [
        "",
        f"{current_time.day}T",
        f"{current_time.month}-",
        f"{current_time.year}-",
    ]:
        time_to_parse = extra + time_to_parse

        # start the test
        capture_post_payload = list()

        def mockpost(*args, **kwargs):
            capture_post_payload.append(kwargs)
            return MockResponse(
                0, queue_test_success_res(), json.dumps(queue_test_success_res())
            )

        monkeypatch.setattr(requests, "post", mockpost)
        result = cli_test_runner.invoke(
            cli,
            [
                "exec",
                str(ap_file),
                "-a",
                mock_api_endpoint(),
                "--schedule-at",
                time_to_parse,
            ],
        )
        assert result.exit_code == 0
        assert (
            f"Success. View {mock_api_endpoint()}/dashboard?sessionId=testSessionId to see the scheduling outcome."
            in result.output
        )
        for payload in capture_post_payload:
            if "json" in payload and "scheduleAt" in payload["json"]:
                assert payload["json"]["scheduleAt"] == expected_time
                break
        else:
            assert (
                False
            ), f"No request was made with a 'scheduleAt' key. {capture_post_payload}"


def test_session_id(cli_test_runner, monkeypatch, ap_file):
    sessionId = "hi_there"

    def mockpost(*args, **kwargs):
        return MockResponse(
            0,
            queue_test_success_res(sessionId),
            json.dumps(queue_test_success_res(sessionId)),
        )

    monkeypatch.setattr(requests, "post", mockpost)
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
        f"Success. View {mock_api_endpoint()}/dashboard?sessionId={sessionId} to see the scheduling outcome."
        in result.output
    )
