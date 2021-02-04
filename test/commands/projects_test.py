import json

import pytest
import responses

from transcriptic import commands


class TestProjects:
    @responses.activate
    def test_projects_invalid(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json="some verbose error",
            status=404,
        )

        with pytest.raises(RuntimeError):
            commands.projects(test_connection)

    @responses.activate
    def test_projects_names_only(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        actual = commands.projects(test_connection, names_only=True)

        expected = {"p123": "Foo"}
        assert actual == expected

    @responses.activate
    def test_projects_deprecated_i(self, test_connection):
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
            actual = commands.projects(test_connection, i=True)

        expected = {"p123": "Foo"}
        assert actual == expected

    @responses.activate
    def test_projects_json_flag(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        actual = commands.projects(test_connection, json_flag=True)

        expected = [{"archived_at": "some datetime", "id": "p123", "name": "Foo"}]
        assert actual == expected

    @responses.activate
    def test_projects_default_return(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_projects"),
            json={
                "projects": [
                    {"archived_at": "some datetime", "id": "p123", "name": "Foo"}
                ]
            },
        )

        actual = commands.projects(test_connection)

        expected = {"p123": "Foo (archived)"}
        assert actual == expected
