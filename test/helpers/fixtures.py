import json

import pytest

from click.testing import CliRunner
from Crypto.PublicKey import RSA


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


@pytest.fixture
def cli_test_runner(temp_tx_dotfile):
    runner = CliRunner(
        env={"TRANSCRIPTIC_CONFIG": str(temp_tx_dotfile)}, mix_stderr=False
    )
    yield runner


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
