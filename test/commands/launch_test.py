import pytest
import responses

from transcriptic import commands
from transcriptic.util import PreviewParameters


class TestLaunch:
    """
    Note: Underlying helper functions are tested separately in `TestUtils` class. This
          uses monkeypatching to mock out those functions.
    """

    project_id = "p123"
    launch_request_id = "lr123"
    quick_launch_id = "quick123"
    protocolname = "protocolname"
    title = "launch_title"
    run_id = "r123"
    mock_baseurl = "http://mock-api/mock"

    @pytest.fixture(scope="function")
    def simple_manifest(self, simple_protocol):
        yield {"format": "python", "license": "MIT", "protocols": [simple_protocol]}

    @pytest.fixture(scope="function")
    def simple_protocol(self):
        yield {
            "name": self.protocolname,
            "display_name": "displayname",
            "categories": [],
            "description": "desc",
            "version": "1.0.0",
            "command_string": "python3 -m protocol.main",
            "inputs": {},
            "preview": {"parameters": {}, "refs": {}},
        }

    @pytest.fixture
    def autoprotocol(self):
        """Make a temp autoprotocol file"""
        yield {
            "instructions": [
                {"op": "provision", "x_human": True},
                {"op": "uncover"},
                {"op": "spin"},
                {"op": "cover"},
            ]
        }

    @pytest.fixture(scope="function")
    def run_protocol(self, autoprotocol):
        return lambda api, manifest, protocol_obj, inputs: autoprotocol

    @pytest.fixture(scope="function")
    def load_manifest(self, simple_manifest):
        return lambda: simple_manifest

    @pytest.fixture(scope="function")
    def load_protocol(self, simple_protocol):
        return lambda manifest, protocol_name: simple_protocol

    @pytest.fixture(scope="function")
    def format_url(self):
        return lambda path: f"{self.mock_baseurl}/{self.project_id}/runs/{self.run_id}"

    @pytest.fixture(scope="function")
    def _get_quick_launch(self):
        return lambda api, protocol_obj, project: {
            "raw_inputs": {"parameters": {"config": {"foo": "bar"}}, "refs": {}}
        }

    @pytest.fixture(scope="function")
    def _get_launch_request(self):
        return lambda api, params, protocol_obj, test: [
            self.launch_request_id,
            {"generation_errors": []},
        ]

    @responses.activate
    def test_local(
        self,
        monkeypatch,
        test_connection,
        _get_launch_request,
        _get_quick_launch,
        format_url,
        load_manifest,
        load_protocol,
        run_protocol,
        local=True,
    ):
        monkeypatch.setattr(commands, "load_manifest", load_manifest)
        monkeypatch.setattr(commands, "load_protocol", load_protocol)
        monkeypatch.setattr(
            commands, "get_project_id", lambda api, project: self.project_id
        )
        monkeypatch.setattr(commands, "_get_launch_request", _get_launch_request)
        monkeypatch.setattr(commands, "_get_quick_launch", _get_quick_launch)
        monkeypatch.setattr(test_connection, "url", format_url)
        monkeypatch.setattr(commands, "run_protocol", run_protocol)
        responses.add(
            responses.POST,
            test_connection.get_route(
                "create_quick_launch", project_id=self.project_id
            ),
            json={"id": self.quick_launch_id},
        )
        responses.add(
            responses.POST,
            test_connection.get_route(
                "resolve_quick_launch_inputs",
                project_id=self.project_id,
                quick_launch_id=self.quick_launch_id,
            ),
            json={"inputs": {"parameters": {}, "refs": {}}},
        )
        # Test that it will run without error since the autoprotocol generated
        # gets dumped out in the terminal and not returned
        commands.launch(
            test_connection,
            protocol=self.protocolname,
            project=self.project_id,
            title=self.title,
            save_input=False,
            local=local,
            accept_quote=True,
            params=None,
        )

    @responses.activate
    def test_not_local(
        self,
        monkeypatch,
        test_connection,
        _get_launch_request,
        _get_quick_launch,
        format_url,
        local=False,
    ):
        monkeypatch.setattr(
            commands, "get_project_id", lambda api, project: self.project_id
        )
        monkeypatch.setattr(commands, "_get_launch_request", _get_launch_request)
        monkeypatch.setattr(commands, "_get_quick_launch", _get_quick_launch)
        monkeypatch.setattr(test_connection, "url", format_url)

        responses.add(
            responses.GET,
            test_connection.get_route("get_protocols", org_id="mock"),
            json=[
                {
                    "id": "protocol123",
                    "name": self.protocolname,
                    "created_at": "today",
                    "package_name": "pkgname",
                    "package_id": "pkg123",
                    "release_id": "rel123",
                    "license": "MIT",
                    "published": True,
                    "display_name": "displayname",
                    "categories": [],
                    "description": "desc",
                    "version": "1.0.0",
                    "command_string": "python3 -m protocol.main",
                    "inputs": {},
                    "preview": {"parameters": {}, "refs": {}},
                }
            ],
        )
        responses.add(
            responses.POST,
            test_connection.get_route(
                "submit_launch_request",
                launch_request_id=self.launch_request_id,
                project_id=self.project_id,
                protocol_id="protocol123",
                title=self.title,
            ),
            json={"id": f"{self.run_id}"},
        )

        actual = commands.launch(
            test_connection,
            protocol=self.protocolname,
            project=self.project_id,
            title=self.title,
            save_input=False,
            local=local,
            accept_quote=True,
            params=None,
        )
        expected = f"{self.mock_baseurl}/{self.project_id}/runs/{self.run_id}"
        assert actual == expected

    @responses.activate
    def test_save_preview(
        self,
        monkeypatch,
        test_connection,
        load_manifest,
        load_protocol,
        _get_launch_request,
        _get_quick_launch,
        format_url,
    ):
        monkeypatch.setattr(commands, "load_manifest", load_manifest)
        monkeypatch.setattr(commands, "load_protocol", load_protocol)
        monkeypatch.setattr(commands, "_get_quick_launch", _get_quick_launch)
        manifest = commands.load_manifest()
        protocol_obj = commands.load_protocol(
            manifest=manifest, protocol_name=self.protocolname
        )
        quick_launch = commands._get_quick_launch(
            test_connection, protocol_obj, self.project_id
        )
        params = dict(parameters=quick_launch["raw_inputs"])
        pp = PreviewParameters(test_connection, params["parameters"], protocol_obj)

        # Assert that the PreviewParameters.preview does not match current manfest object
        assert manifest["protocols"][0].get("preview") == protocol_obj.get("preview")
        assert manifest["protocols"][0].get("preview") != pp.preview.get("preview")

        # Merge PreviewParameters.preview into a copy of the manifest
        pp.merge(manifest)

        # Assert that the merge placed the PreviewParameters.preview into the merged_manifest
        assert pp.merged_manifest["protocols"][0].get("preview") != protocol_obj.get(
            "preview"
        )
        assert pp.merged_manifest["protocols"][0].get("preview") == pp.preview.get(
            "preview"
        )
