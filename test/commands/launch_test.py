import json

import pytest

import responses

from transcriptic import commands
from transcriptic.util import PreviewParameters


class TestLaunch:
    """
    Note: Underlying helper functions are tested separately in `TestUtils` class. This
          uses monkeypatching to mock out those functions.
    """

    project_id = "pr123"

    @pytest.fixture
    def valid_json_file(self, tmpdir):
        path = tmpdir.mkdir("foo").join("valid-input.json")
        path.write(json.dumps({"refs": {}, "instructions": []}))
        yield path

    @pytest.fixture
    def valid_manifest_file(self, tmpdir):
        path = tmpdir.join("manifest.json")
        path.write(
            json.dumps(
                {
                    "format": "python",
                    "license": "MIT",
                    "protocols": [
                        {
                            "name": "protocolname",
                            "display_name": "displayname",
                            "categories": [],
                            "description": "desc",
                            "version": "1.0.0",
                            "command_string": "python3 -m protocol.main",
                            "inputs": {},
                            "preview": {"parameters": {}, "refs": {}},
                        }
                    ],
                }
            )
        )
        yield path

    @pytest.fixture(scope="function")
    def simple_manifest(self, simple_protocol):
        yield {"format": "python", "license": "MIT", "protocols": [simple_protocol]}

    @pytest.fixture(scope="function")
    def simple_protocol(self):
        yield {
            "name": "protocolname",
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

    @pytest.fixture(scope="function")
    def format_url(self):
        return lambda path: f"http://mock-api/mock/p123/runs/r123"

    @pytest.fixture(scope="function")
    def _get_quick_launch(self):
        return lambda api, protocol_obj, project: {
            "raw_inputs": {"parameters": {"config": {"foo": "bar"}}, "refs": {}}
        }

    @pytest.fixture(scope="function")
    def _get_launch_request(self):
        return lambda api, params, protocol_obj, test: [
            "lr123",
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
            json={"id": "quick123"},
        )
        responses.add(
            responses.POST,
            test_connection.get_route(
                "resolve_quick_launch_inputs",
                project_id=self.project_id,
                quick_launch_id="quick123",
            ),
            json={"inputs": {"parameters": {}, "refs": {}}},
        )
        actual = commands.launch(
            test_connection,
            protocol="protocolname",
            project=self.project_id,
            title="launch_title",
            save_input=False,
            local=local,
            accept_quote=True,
            params=None,
        )
        expected = "http://mock-api/mock/p123/runs/r123"
        assert actual == expected

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
        monkeypatch.setattr(commands, "get_project_id", lambda api, project: "p123")
        monkeypatch.setattr(commands, "_get_launch_request", _get_launch_request)
        monkeypatch.setattr(commands, "_get_quick_launch", _get_quick_launch)
        monkeypatch.setattr(test_connection, "url", format_url)

        responses.add(
            responses.GET,
            test_connection.get_route("get_protocols", org_id="mock"),
            json=[
                {
                    "id": "protocol123",
                    "name": "protocolname",
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
                launch_request_id="lr123",
                project_id="p123",
                protocol_id="protocol123",
                title="launch_title",
            ),
            json={"id": "r123"},
        )

        actual = commands.launch(
            test_connection,
            protocol="protocolname",
            project="p123",
            title="launch_title",
            save_input=False,
            local=local,
            accept_quote=True,
            params=None,
        )
        expected = "http://mock-api/mock/p123/runs/r123"
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
        valid_manifest_file,
    ):
        monkeypatch.setattr(commands, "load_manifest", load_manifest)
        monkeypatch.setattr(commands, "load_protocol", load_protocol)
        monkeypatch.setattr(commands, "_get_quick_launch", _get_quick_launch)
        manifest = commands.load_manifest()
        protocol_obj = commands.load_protocol(
            manifest=manifest, protocol_name="protocolname"
        )
        quick_launch = commands._get_quick_launch(
            test_connection, protocol_obj, self.project_id
        )
        params = dict(parameters=quick_launch["raw_inputs"])
        pp = PreviewParameters(test_connection, params["parameters"], protocol_obj)

        assert manifest["protocols"][0].get("preview") == protocol_obj.get("preview")
        assert manifest["protocols"][0].get("preview") != pp.preview.get("preview")
        pp.merge(manifest)
        assert pp.merged_manifest["protocols"][0].get("preview") != protocol_obj.get(
            "preview"
        )
        assert pp.merged_manifest["protocols"][0].get("preview") == pp.preview.get(
            "preview"
        )
