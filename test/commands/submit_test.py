import json

import pytest
import responses

from transcriptic import commands


class TestSubmit:
    """
    Note: Underlying helper functions are tested separately in `TestUtils` class. This
          uses monkeypatching to mock out those functions.
    """

    @pytest.fixture
    def valid_json_file(self, tmpdir):
        path = tmpdir.mkdir("foo").join("valid-input.json")
        path.write(json.dumps({"refs": {}, "instructions": []}))
        yield path

    def test_invalid_pm(self, monkeypatch, test_connection):
        monkeypatch.setattr(commands, "is_valid_payment_method", lambda api, pm: False)

        with pytest.raises(RuntimeError) as error:
            commands.submit(test_connection, "some file", "some project", pm="invalid")

        assert f"{error.value}" == (
            "Payment method is invalid. Please specify a payment "
            "method from `transcriptic payments` or not specify the "
            "`--payment` flag to use the default payment method."
        )

    def test_invalid_project(self, monkeypatch, test_connection):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: False)

        with pytest.raises(RuntimeError) as error:
            commands.submit(test_connection, "some file", "invalid_project")

        assert f"{error.value}" == "Invalid project invalid_project specified"

    def test_invalid_file(self, monkeypatch, test_connection, tmpdir):
        path = tmpdir.mkdir("foo").join("invalid-input.txt")
        path.write("this is not json")

        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        with pytest.raises(RuntimeError) as error:
            commands.submit(test_connection, path, "project name")

        assert (
            f"{error.value}"
            == "Error: Could not submit since your manifest.json file is improperly "
            "formatted."
        )

    @responses.activate
    def test_valid_submission(self, monkeypatch, test_connection, valid_json_file):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        responses.add(
            responses.POST,
            test_connection.get_route("submit_run", project_id="p123"),
            json={"id": "r123"},
        )

        actual = commands.submit(test_connection, valid_json_file, "project name")

        expected = "http://mock-api/mock/p123/runs/r123"
        assert actual == expected

    @responses.activate
    def test_submit_exception_handling(
        self, monkeypatch, test_connection, valid_json_file
    ):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        responses.add(
            responses.POST,
            test_connection.get_route("submit_run", project_id="p123"),
            json="some verbose error",
            status=404,
        )

        with pytest.raises(RuntimeError) as error:
            commands.submit(test_connection, valid_json_file, "project name")

        assert "Error: Couldn't create run (404)" in f"{error.value}"
