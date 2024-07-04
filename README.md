Mock SSH Server
-----------------

Simple SSH Mock Server for E2E testing purposes, e.g. with [Testcontainers](https://testcontainers.com/).

Installation
-----------

## Python

```bash
pip install ssh-mock
# Create commands.yml first
# Start Mock
ssh-mock
```

## Docker

See docker-compose.yml or run:

```bash
# Create commands.yml first
# Run Mock Server:
docker run --rm -p 5050:5050 -v ./commands.yml:/usr/src/app/commands.yml ghcr.io/danielhabenicht/mock-ssh:0.2.2
# Try it out
ssh localhost -p 5050
exec echo Hello World!
```

## YAML Configuration

```yaml	title=commands.yml
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


## Thanks

This was initally a fork of [https://github.com/d1618033/fake-ssh](https://github.com/d1618033/fake-ssh). Thanks [David](https://github.com/d1618033) for your work!