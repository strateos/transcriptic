import json

import pytest

from click.testing import CliRunner
from Crypto.PublicKey import RSA
from transcriptic import commands
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
        "feature_groups": ["can_submit_autoprotocol", "can_upload_packages"],
    }
    with open(str(path), "w") as f:
        json.dump(config, f)
    return path


@pytest.fixture()
def temp_ssh_key(tmpdir_factory):
    dir_path = tmpdir_factory.mktemp("ssh")
    private_key_path = str(dir_path.join("private.pem"))
    public_key_path = str(dir_path.join("public.pem"))
    private_key = RSA.generate(2048)
    with open(private_key_path, "wb") as private_key_file:
        private_key_file.write(private_key.exportKey("PEM"))
    pubkey = private_key.publickey()
    with open(public_key_path, "wb") as public_key_file:
        public_key_file.write(pubkey.exportKey("OpenSSH"))
    yield private_key_path, public_key_path


@pytest.fixture
def cli_test_runner(temp_tx_dotfile):
    runner = CliRunner(
        env={"TRANSCRIPTIC_CONFIG": str(temp_tx_dotfile)}, mix_stderr=False
    )
    yield runner
    # _TODO_ ^ try using this


def test_kebab_case(cli_test_runner):
    result = cli_test_runner.invoke(cli, ["--help"])
    command_str = result.output.split("Commands:\n")[1]
    commands = [x.strip() for x in command_str.split("\n") if x != ""]
    is_kebab = lambda x: x.islower() and ("_" not in x)
    assert all([is_kebab(cmd) for cmd in commands])


def test_login_nonexistent_key_path(cli_test_runner):
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", "/temp/path/invalid_key.pem"],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert "Invalid value for '--rsa-key'" in result.stderr


def test_login_random_file_for_key(cli_test_runner, tmpdir_factory):
    path = tmpdir_factory.mktemp("foo").join("random-file")
    with open(str(path), "w") as fh:
        fh.write("this is not an rsa key")
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", str(path)],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert (
        "Error loading RSA key: Could not parse the specified RSA Key, "
        "ensure it is a PRIVATE key in PEM format" in result.stderr
    )
    assert result.exit_code == 1


def test_login_public_key(cli_test_runner, temp_ssh_key):
    (private_key_path, public_key_path) = temp_ssh_key
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", public_key_path],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert "Error connecting to host: This is not a private key" in result.output
    assert result.exit_code == 1


def test_projects_exception(cli_test_runner, monkeypatch):
    def mocked_exception(api, i, json_flag, names_only):
        raise RuntimeError("Some runtime error")

    monkeypatch.setattr(commands, "projects", mocked_exception)

    result = cli_test_runner.invoke(
        cli,
        ["projects"],
    )
    assert result.stderr == (
        "There was an error listing the projects in your "
        "organization. Make sure your login details are correct.\n"
    )


def test_projects_names_only(cli_test_runner, monkeypatch):
    mocked_return = {"p123": "Foo"}
    monkeypatch.setattr(
        commands, "projects", lambda api, i, json_flag, names_only: mocked_return
    )

    result = cli_test_runner.invoke(
        cli,
        ["projects", "--names"],
    )
    assert result.output == f"{mocked_return}\n"


def test_projects_json_flag(cli_test_runner, monkeypatch):
    mocked_return = [{"archived_at": "some datetime", "id": "p123", "name": "Foo"}]
    monkeypatch.setattr(
        commands, "projects", lambda api, i, json_flag, names_only: mocked_return
    )

    result = cli_test_runner.invoke(
        cli,
        ["projects", "--json"],
    )
    assert result.output == f"{json.dumps(mocked_return)}\n"


def test_projects_default(cli_test_runner, monkeypatch):
    mocked_return = {"p123": "Foo (archived)"}
    monkeypatch.setattr(
        commands, "projects", lambda api, i, json_flag, names_only: mocked_return
    )

    result = cli_test_runner.invoke(
        cli,
        ["projects"],
    )
    assert result.output == (
        "\n"
        "                                   PROJECTS:\n"
        "                                   \n"
        "              PROJECT NAME              |               PROJECT ID               \n"
        "--------------------------------------------------------------------------------\n"
        "Foo (archived)                          |                  p123                  \n"
        "--------------------------------------------------------------------------------\n"
    )


def test_submit_exception_handling(cli_test_runner, monkeypatch):
    runtime_error = "Some runtime error message"

    def mocked_exception(api, file, project, title, test, pm):
        raise RuntimeError(runtime_error)

    monkeypatch.setattr(commands, "submit", mocked_exception)
    result = cli_test_runner.invoke(cli, ["submit", "--project", "some project"])
    assert result.stderr == f"{runtime_error}\n"
    assert result.exit_code == 1


def test_submit_success(cli_test_runner, monkeypatch):
    mock_url = "http://mock-api/mock/p123/runs/r123"
    monkeypatch.setattr(
        commands, "submit", lambda api, file, project, title, test, pm: mock_url
    )
    result = cli_test_runner.invoke(cli, ["submit", "--project", "some project"])
    assert result.output == f"Run created: {mock_url}\n"
