import os
import time
import paramiko
import pytest
from ssh_mock import CommandFailure, Server
import threading


@pytest.fixture
def server():
    def handler(command: str) -> str:
        if command == "ls":
            return "file1\nfile2"
        elif command.startswith("echo"):
            return command[4:].strip()
        raise CommandFailure(f"Unknown command {command}")

    mock_server = Server(command_handler=handler)
    with mock_server as server_fixture:
        thread = threading.Thread(target=server_fixture._run)
        thread.daemon = True
        thread.start()
        yield server_fixture


def create_client(server, password="", ssh_key_file=None):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(
        hostname=server.host,
        port=server.port,
        username="root",
        allow_agent=False,
        look_for_keys=False,
    )
    if ssh_key_file is not None:
        with open(ssh_key_file) as f:
            kwargs["pkey"] = paramiko.RSAKey.from_private_key(f)
    else:
        kwargs["password"] = password
    c.connect(**kwargs)
    return c


@pytest.mark.parametrize(
    "auth",
    [
        {"password": ""},
        {
            "ssh_key_file": os.path.join(
                os.path.dirname(__file__), "data", "id_rsa"
            )
        },
    ],
)
@pytest.mark.parametrize(
    "command,result",
    [
        ("ls\n", "file1\nfile2"),
        ("echo 42\n", "42"),
    ],
)
def test_successful_command(server, auth, command, result):
    client = create_client(server, **auth)
    _stdin, stdout, stderr = client.exec_command(command)
    out_string = stdout.read().decode()
    assert out_string == result, stderr.read()
