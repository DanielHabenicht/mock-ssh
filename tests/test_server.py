import os
import subprocess

import pytest


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
        ("ls", "file1\nfile2"),
        ("echo 42", "42"),
    ],
)
def test_successful_command(server, auth, command, result):
    (stdout, stderr) = subprocess.Popen(
        f"echo '{command}' | ssh -o StrictHostKeyChecking=no -p {server.split(':')[1]} {server.split(':')[0]}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate()

    # client = create_client(server, **auth)
    # _stdin, stdout, stderr = client.exec_command(command, timeout=2)
    assert stdout.decode() == result, stderr.decode()
    # client.close()
