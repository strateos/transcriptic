import json

import pytest
from click.testing import CliRunner
from transcriptic.cli import cli


@pytest.fixture(scope="session")
def temp_tx_dotfile(tmpdir_factory):
    path = tmpdir_factory.mktemp("config").join(".transcriptic")
    config = {
        "email": "somebody@transcriptic.com",
        "token": "foobarinvalid",
        "organization_id": "transcriptic",
        "api_root": "http://foo:5555",
        "analytics": True,
        "user_id": "ufoo2",
        "feature_groups": [
            "can_submit_autoprotocol",
            "can_upload_packages"
        ]
    }
    with open(str(path), "w") as f:
        json.dump(config, f)
    return path


@pytest.fixture
def cli_test_runner(temp_tx_dotfile):
    runner = CliRunner(
        env={
            'TRANSCRIPTIC_CONFIG': str(temp_tx_dotfile)
        }
    )
    yield runner


def test_kebab_case(cli_test_runner):
    result = cli_test_runner.invoke(cli, ['--help'])
    command_str = result.output.split("Commands:\n")[1]
    commands = [x.strip() for x in command_str.split("\n") if x != '']
    is_kebab = lambda x: x.islower() and ("_" not in x)
    assert(all([is_kebab(cmd) for cmd in commands]))
