import responses

from requests.exceptions import ConnectionError
from transcriptic.config import Connection
from transcriptic.sampledata.project import sample_project_attr
from transcriptic.sampledata.run import sample_run_attr
from transcriptic.util import load_sampledata_json


class MockConnection(Connection):
    """
    MockConnection object used for previewing Juypter objects without establishing a
    connection.

    Example Usage:

        .. code-block:: python

            mock_connection = MockConnection()
            mock_connection.projects()
            myRun = Run('r123')
    """

    def __init__(self, *args, organization_id="sample-org", **kwargs):
        super().__init__(*args, organization_id=organization_id, **kwargs)

    @responses.activate
    def _req_call(self, method, route, **kwargs):
        self._register_mocked_responses()
        try:
            return super()._req_call(method, route, **kwargs)
        except ConnectionError:
            # Default raised exception lists all routes which is very verbose
            if self.verbose:
                raise
            else:
                raise ConnectionError(f"Mocked route not implemented: {route}")

    def _register_mocked_responses(self):
        # TODO: Everything is hardcoded right now. Move to Jinja
        # Register Project routes
        responses.add(
            responses.GET,
            self.get_route("get_project", project_id="p123"),
            json=sample_project_attr,
            status=200,
        )
        responses.add(
            responses.GET,
            self.get_route("deref_route", obj_id="p123"),
            json=sample_project_attr,
            status=200,
        )
        responses.add(
            responses.GET,
            self.get_route("get_projects", org_id="sample-org"),
            json=load_sampledata_json("sample-org-projects.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            self.get_route("get_project_runs", org_id="sample-org", project_id="p123"),
            json=load_sampledata_json("p123-runs.json"),
        )
        # Register Run routes
        responses.add(
            responses.GET,
            self.get_route("deref_route", obj_id="r123"),
            json=sample_run_attr,
            status=200,
        )
        # Register Container routes
        responses.add(
            responses.GET,
            self.get_route("deref_route", obj_id="ct123"),
            json=load_sampledata_json("ct123.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            self.get_route("deref_route", obj_id="ct124"),
            json=load_sampledata_json("ct124.json"),
            status=200,
        )
        # Register Dataset routes
        for data_id in ["d123", "d124", "d125", "d126", "d127"]:
            # Note: `match_querystring` is important for correct resolution
            responses.add(
                responses.GET,
                self.get_route("dataset_short", data_id=data_id),
                json=load_sampledata_json(f"{data_id}.json"),
                status=200,
                match_querystring=True,
            )
            responses.add(
                responses.GET,
                self.get_route("dataset", data_id=data_id, key="*"),
                json=load_sampledata_json(f"{data_id}-raw.json"),
                status=200,
                match_querystring=True,
            )
