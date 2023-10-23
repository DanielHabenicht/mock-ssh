Mock SSH Server
-----------------

Installation
-----------

## Python

```
pip install ssh-mock
```

## Docker

See docker-compose.yml or run:

```

```

## YML Configuration

```yaml	
version: "3.7"
commands:
# Simple command
 - command: echo hello
   stdout: "Hello World!"
   returncode: 0
# Command matching regex
 - command: interface.*
   stdout: ""
# Return values from command via JINJA template
 - command: exec echo.*
   stdout_template: "{{command[9:]|trim|trim('''')|trim('\"')}}"
   returncode: 0
# Modify the Hostname
 - command: enable
   stdout: "Password"
   modify_host: HOST#
   returncode: 0
# Use multiple lines
 - command: show users
   stdout: "    Line       User       Host(s)              Idle       Location\n*  1 vty 0     rootuser   idle                 00:00:00\n                                                          example.test.de\n\n  Interface    User               Mode         Idle     Peer Address\n\n"
   returncode: 0
 - command: show interfaces description
   stdout: | 
    Interface                      Status         Protocol Description
    Vl1                            up             up
    Vl308                          up             up
    Gi1/0/1                        up             up       Access Port
    Gi1/0/12                       down           down     Access Port
    Gi1/1/1                        down           down
    Gi1/1/2                        down           down
    Te1/1/3                        down           down
    Te1/1/4                        up             up
```

# Outdated documentation:

## Blocking Server

A blocking server is often used for development purposes.

Simply write yourself a `server.py` file:

```python
from typing import Optional
from ssh_mock import Server


def handler(command: str) -> Optional[str]:
    if command.startswith("ls"):
        return "file1\nfile2\n"
    elif command.startswith("echo"):
        return command[4:].strip() + "\n"

if __name__ == "__main__":
    Server(command_handler=handler, port=5050).run_blocking()

```

And run it:

```
$ python3 server.py
```

In a separate terminal, run:

```
$ ssh root@127.0.0.1 -p 5050 echo 42
42
                                                                         
$ ssh root@127.0.0.1 -p 5050 ls
file1
file2
```

(if you are prompted for a password, you can leave it blank)

Note how you need to specify a non standard port (5050). Using the standard port (22) would require root permissions
and is probably unsafe.


## Non-Blocking Server

A non blocking server is often used in tests. 

This server runs in a thread and allows you to run some tests in parallel.

```python
import paramiko
import pytest

from mock_ssh import Server


def handler(command):
    if command == "ls":
        return "file1\nfile2\n"


@pytest.fixture
def server():
    with Server(command_handler=handler) as server:
        yield server


def my_ls(host, port):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(hostname=host,
              port=port,
              username="root",
              password="",
              allow_agent=False,
              look_for_keys=False)
    return c.exec_command("ls")[1].read().decode().splitlines()


def test_ls(server):
    assert my_ls(server.host, server.port) == ["file1", "file2"]

```


## Thanks

This was initally a fork of [https://github.com/d1618033/fake-ssh](https://github.com/d1618033/fake-ssh). Thanks [David](https://github.com/d1618033) for your work!