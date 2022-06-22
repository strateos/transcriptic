import pandas as pd
import pytest
import requests

from transcriptic.sampledata import load_sample_container
from transcriptic.sampledata.connection import MockConnection
from transcriptic.sampledata.container import sample_container_attr
from transcriptic.sampledata.dataset import (
    ABSORBANCE_DATASETS,
    load_sample_dataset,
    sample_dataset_attr,
)
from transcriptic.sampledata.project import load_sample_project, sample_project_attr
from transcriptic.sampledata.run import load_sample_run, sample_run_attr
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
        assert mock_connection.runs(project_id="p123") == [
            {**data["attributes"], "id": data["id"]}
            for data in load_sampledata_json("p123-runs.json")["data"]
        ]
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

        containers = run.containers
        assert len(containers) == 2
        assert containers.loc[0].ContainerId == "ct123"
        assert containers.loc[1].ContainerId == "ct124"

        instructions = run.instructions
        assert len(instructions) == 2
        assert instructions.loc[0].Id == "i123"
        assert instructions.loc[1].Id == "i124"

        # all instructions have a `generated_container` attribute, if none generated, it is empty list
        expected_generated_containers = [
            {"id": "ct123", "label": "container_generated"}
        ]
        assert (
            instructions.loc[0].Instructions.generated_containers
            == expected_generated_containers
        )
        assert instructions.loc[1].Instructions.generated_containers == []

        data = run.data
        assert len(data) == 1
        assert data.loc[0].Name == "OD600"

        datasets = run.Datasets
        assert len(datasets) == 1

    def test_jupyter_container(self):
        from transcriptic import Container

        mock_connection = MockConnection()

        with pytest.raises(
            requests.exceptions.ConnectionError, match="Mocked route not implemented"
        ):
            Container("invalid-id")

        container = Container("ct123")
        assert container.id == "ct123"
        assert container.connection == mock_connection
        assert container.attributes == sample_container_attr

    def test_jupyter_dataset(self):
        from transcriptic import Dataset

        mock_connection = MockConnection()

        with pytest.raises(
            requests.exceptions.ConnectionError, match="Mocked route not implemented"
        ):
            Dataset("invalid-id")

        dataset = Dataset("d123")
        assert dataset.id == "d123"
        assert dataset.connection == mock_connection
        assert dataset.attributes == sample_dataset_attr

        assert dataset.analysis_tool is None
        assert dataset.analysis_tool_version is None
        assert dataset.attachments == {}
        assert dataset.container.name == "VbottomPlate"
        assert dataset.data_type == "platereader"
        assert dataset.operation == "absorbance"
        assert dataset.raw_data == {
            "a1": [0.05],
            "a2": [0.04],
            "a3": [0.06],
            "b1": [1.21],
            "b2": [1.13],
            "b3": [1.32],
            "c1": [2.22],
            "c2": [2.15],
            "c3": [2.37],
        }
        assert len(dataset.data.columns) == 9

    def test_load_sample_objects(self):
        mock_connection = MockConnection()

        project = load_sample_project()
        assert project.attributes == sample_project_attr
        assert project.connection == mock_connection

        run = load_sample_run()
        assert run.attributes == sample_run_attr
        assert run.connection == mock_connection

        for dataset_id in ABSORBANCE_DATASETS:
            dataset = load_sample_dataset(dataset_id)
            assert dataset.attributes == load_sampledata_json(f"{dataset_id}.json")
            assert dataset.connection == mock_connection

        for container_id in ["ct123", "ct124"]:
            container = load_sample_container(container_id)
            assert container.attributes == load_sampledata_json(f"{container_id}.json")
            assert container.connection == mock_connection
