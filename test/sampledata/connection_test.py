import pandas as pd
import pytest
import requests

from transcriptic.sampledata.connection import MockConnection
from transcriptic.sampledata.project import sample_project_attr, load_sample_project
from transcriptic.sampledata.run import sample_run_attr, load_sample_run
from transcriptic.util import load_sampledata_json


class TestMockConnection:
    def test_defaults(self):
        assert MockConnection().organization_id == "sample-org"

    def test_not_registered(self):
        with pytest.raises(
            requests.exceptions.ConnectionError, match="Mocked route not implemented"
        ):
            MockConnection().project(project_id="invalid-project")
        with pytest.raises(
            requests.exceptions.ConnectionError,
            match="Connection refused by Responses - the call doesn't "
            "match any registered mock.",
        ):
            MockConnection(verbose=True).project(project_id="invalid-project")

    def test_registered_responses(self):
        mock_connection = MockConnection()
        assert mock_connection.project(project_id="p123") == sample_project_attr
        assert (
            mock_connection._get_object(obj_id="p123", obj_type="project")
            == sample_project_attr
        )
        assert (
            mock_connection.projects()
            == load_sampledata_json("sample-org-projects.json")["projects"]
        )
        assert mock_connection.runs(project_id="p123") == load_sampledata_json(
            "p123-runs.json"
        )
        assert mock_connection._get_object(obj_id="r123") == sample_run_attr

    def test_jupyter_project(self):
        from transcriptic import Project

        mock_connection = MockConnection()

        with pytest.raises(
            TypeError, match="invalid-id is not found in your projects."
        ):
            Project("invalid-id")

        project = Project("p123")
        assert project.id == "p123"
        assert project.name == "sample project"
        assert project.connection == mock_connection
        assert project.attributes == sample_project_attr

        project_runs = project.runs()
        assert type(project_runs) == pd.DataFrame
        assert len(project_runs) == 1
        assert project_runs.loc[0].id == "r123"
        assert project_runs.loc[0].Name == "Sample Run"

    def test_jupyter_run(self):
        from transcriptic import Run

        mock_connection = MockConnection()

        with pytest.raises(
            requests.exceptions.ConnectionError, match="Mocked route not implemented"
        ):
            Run("invalid-id")

        run = Run("r123")
        assert run.id == "r123"
        assert run.connection == mock_connection
        assert run.attributes == sample_run_attr

    def test_load_sample_objects(self):
        mock_connection = MockConnection()

        project = load_sample_project()
        assert project.attributes == sample_project_attr
        assert project.connection == mock_connection

        run = load_sample_run()
        assert run.attributes == sample_run_attr
        assert run.connection == mock_connection
