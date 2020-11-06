from transcriptic.config import Connection
from requests.exceptions import ConnectionError

import responses

from transcriptic.sampledata.project import sample_project_attr
from transcriptic.util import load_sampledata_json


class MockConnection(Connection):
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
        # Register Project routes
        # TODO: Everything is hardcoded right now. Move to Jinja
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
