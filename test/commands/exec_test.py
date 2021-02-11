# import json

# import requests

# from click.testing import CliRunner
# from transcriptic.cli import cli

# from ..helpers.mockAPI import MockResponse


# # Structure of the response object from SCLE
# def bool_success_res():
#     return {"success": True}


# def good_autoprotocol_file():
#     return "test/autoprotocol/singleTransfer.json"


# def mock_api_endpoint():
#     return "foo.bar.baz"


# def test_good_autoprotocol(monkeypatch):
#     def mockpost(*args, **kwargs):
#         return MockResponse(0, bool_success_res(), json.dumps(bool_success_res()))

#     monkeypatch.setattr(requests, "post", mockpost)
#     runner = CliRunner()
#     result = runner.invoke(
#         cli, ["exec", good_autoprotocol_file(), "-a", mock_api_endpoint()]
#     )
#     assert result.exit_code == 0
#     assert (
#         f"Success. View {mock_api_endpoint()} to see the scheduling outcome."
#         in result.output
#     )


# def test_bad_autoprotocol():
#     runner = CliRunner()
#     result = runner.invoke(cli, ["exec", "bad-file-handle", "-a", mock_api_endpoint()])
#     assert result.exit_code != 0
#     assert "Invalid value for '[AUTOPROTOCOL]': Could not open file" in result.output


# def test_bad_deviceset():
#     runner = CliRunner()
#     result = runner.invoke(
#         cli,
#         [
#             "exec",
#             good_autoprotocol_file(),
#             "--device-set",
#             "bad-file-handle",
#             "-a",
#             mock_api_endpoint(),
#         ],
#     )
#     assert result.exit_code != 0
#     assert (
#         "Invalid value for '--device-set' / '-d': Could not open file: bad-file-handle:"
#         in result.output
#     )


# def test_bad_api_response(monkeypatch):
#     def mockpost(*args, **kwargs):
#         return MockResponse(0, "not-json", "not-json")

#     monkeypatch.setattr(requests, "post", mockpost)
#     runner = CliRunner()
#     result = runner.invoke(
#         cli, ["exec", good_autoprotocol_file(), "-a", mock_api_endpoint()]
#     )
#     assert result.exit_code == 0
#     assert "Error: " in result.output
