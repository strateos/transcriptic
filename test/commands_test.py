import json

import pytest
import responses

from transcriptic import commands


class TestUtils:
    @responses.activate
    def test_valid_payment_method_true(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_payment_methods"),
            json=[{"id": "someId", "is_valid": True}],
        )
        assert commands.is_valid_payment_method(test_connection, "someId")

    @responses.activate
    def test_valid_payment_method_false(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_payment_methods"),
            json=[{"id": "someId", "is_valid": True}],
        )
        assert not commands.is_valid_payment_method(test_connection, "invalidId")


class TestProjects:
    @responses.activate
    def test_projects_invalid(self, test_connection, capsys):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json="some verbose error",
            status=404,
        )

        commands.projects(test_connection)

        captured = capsys.readouterr()
        assert captured.err == (
            "There was an error listing the projects in your "
            "organization. Make sure your login details are correct.\n"
        )

    @responses.activate
    def test_projects_names_only(self, test_connection, capsys):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        ret = commands.projects(test_connection, names_only=True)

        expected = {"p123": "Foo"}
        assert ret == expected
        captured = capsys.readouterr()
        assert captured.out == f"{expected}\n"

    @responses.activate
    def test_projects_deprecated_i(self, test_connection, capsys):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        with pytest.warns(FutureWarning):
            ret = commands.projects(test_connection, i=True)

        expected = {"p123": "Foo"}
        assert ret == expected
        captured = capsys.readouterr()
        assert captured.out == f"{expected}\n"

    @responses.activate
    def test_projects_json_flag(self, test_connection, capsys):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        ret = commands.projects(test_connection, json_flag=True)

        expected = [{"archived_at": "some datetime", "id": "p123", "name": "Foo"}]
        assert ret == expected
        captured = capsys.readouterr()
        assert captured.out == f"{json.dumps(expected)}\n"

    @responses.activate
    def test_projects_default_return(self, test_connection, capsys):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        commands.projects(test_connection)

        captured = capsys.readouterr()
        assert captured.out == (
            "\n"
            "                                   PROJECTS:\n"
            "                                   \n"
            "              PROJECT NAME              |               PROJECT ID               \n"
            "--------------------------------------------------------------------------------\n"
            "Foo (archived)                          |                  p123                  \n"
            "--------------------------------------------------------------------------------\n"
        )


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

    def test_invalid_pm(self, monkeypatch, test_connection, capsys):
        monkeypatch.setattr(commands, "is_valid_payment_method", lambda api, pm: False)

        commands.submit(test_connection, "some file", "some project", pm="invalid")

        captured = capsys.readouterr()
        assert captured.err == (
            "Payment method is invalid. Please specify a payment "
            "method from `transcriptic payments` or not specify the "
            "`--payment` flag to use the default payment method.\n"
        )

    def test_invalid_project(self, monkeypatch, test_connection, capsys):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: False)

        commands.submit(test_connection, "some file", "invalid_project")

        captured = capsys.readouterr()
        assert captured.err == "Invalid project invalid_project specified\n"

    def test_invalid_file(self, monkeypatch, test_connection, capsys, tmpdir):
        path = tmpdir.mkdir("foo").join("invalid-input.txt")
        path.write("this is not json")

        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        commands.submit(test_connection, path, "project name")

        captured = capsys.readouterr()
        assert (
            captured.err
            == "Error: Could not submit since your manifest.json file is improperly "
            "formatted.\n"
        )

    @responses.activate
    def test_valid_submission(
        self, monkeypatch, test_connection, capsys, valid_json_file
    ):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        responses.add(
            responses.POST,
            test_connection.get_route("submit_run", project_id="p123"),
            json={"id": "r123"},
        )

        commands.submit(test_connection, valid_json_file, "project name")

        captured = capsys.readouterr()
        assert captured.out == "Run created: http://mock-api/mock/p123/runs/r123\n"

    @responses.activate
    def test_submit_exception_handling(
        self, monkeypatch, test_connection, capsys, valid_json_file
    ):
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")

        responses.add(
            responses.POST,
            test_connection.get_route("submit_run", project_id="p123"),
            json="some verbose error",
            status=404,
        )

        commands.submit(test_connection, valid_json_file, "project name")

        captured = capsys.readouterr()
        assert "Error: Couldn't create run (404)" in captured.err
