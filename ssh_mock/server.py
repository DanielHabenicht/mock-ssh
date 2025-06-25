import errno
import logging
import re
import selectors
import socket
import threading
from typing import Dict, Optional

import yaml
from jinja2 import BaseLoader, Environment

from .command import (
    CommandHandler,
    CommandHandlerResult,
    CommandHandlerWrapped,
    CommandResult,
    command_handler_wrapper,
)
from .connection_handler import ConnectionHandler
from .utils import suppress


def load_config_file(
    commands_file: str, command_handler: CommandHandler
) -> (CommandHandlerWrapped, Dict[str, str]):  # type: ignore
    with open(commands_file, "r", encoding="utf-8") as stream:
        try:
            config_yaml = yaml.safe_load(stream)
            commands = config_yaml["commands"]
            vars = config_yaml["initial_state"]
        except yaml.YAMLError as exc:
            logging.error(exc)
            raise

    def new_command_handler(
        command: str, state: Dict[str, str]
    ) -> CommandHandlerResult:
        res = command_handler(command)
        if res is not None:
            return res

        for cmd in commands:
            regex = re.compile(cmd["command"])
            possible_match = regex.match(command)
            if possible_match:
                result = CommandResult()
                if "stdout_template" in cmd:
                    template = Environment(loader=BaseLoader).from_string(
                        cmd["stdout_template"]
                    )

                    result.stdout = template.render(
                        {
                            **state,
                            "command": command,
                        }
                    )

                if "update_state" in cmd:
                    for key in cmd["update_state"].keys():
                        key_template = Environment(
                            loader=BaseLoader
                        ).from_string(key)
                        value_template = Environment(
                            loader=BaseLoader
                        ).from_string(cmd["update_state"][key])

                        key_rendered = key_template.render(
                            {
                                **state,
                                "match": possible_match,
                                command: command,
                            }
                        )
                        value_rendered = value_template.render(
                            {
                                **state,
                                "match": possible_match,
                                command: command,
                            }
                        )

                        state["vars"][key_rendered] = value_rendered
                        logging.info(
                            "Updated state: %s = %s",
                            key_rendered,
                            value_rendered,
                        )

                elif "stdout" in cmd:
                    result.stdout = cmd["stdout"]
                if "stderr" in cmd:
                    result.stderr = cmd["stderr"]
                if "returncode" in cmd:
                    result.returncode = cmd["returncode"]
                if "modify_host" in cmd:
                    state["_host"] = cmd["modify_host"]
                    logging.info(
                        "Modified commandline Host: '%s' => '%s'",
                        state["_host"],
                        cmd["modify_host"],
                    )
                else:
                    result.returncode = 0
                return result
        return None

    return command_handler_wrapper(new_command_handler), vars


class Server:
    def __init__(
        self,
        command_handler: CommandHandler,
        commands_file: str = None,
        host: str = "127.0.0.1",
        port: int = 0,
        default_line_ending: str = "\n",
    ):
        self._socket: Optional[socket.SocketIO] = None
        self.host: str = host
        self._port: int = port
        self.inital_state = {}
        if commands_file is not None:
            self._command_handler, self.inital_state = load_config_file(
                commands_file=commands_file, command_handler=command_handler
            )
        else:
            self._command_handler: CommandHandlerWrapped = (
                command_handler_wrapper(command_handler)
            )

        if "_host" not in self.inital_state:
            self.inital_state["_host"] = host

        self._default_line_ending: str = default_line_ending

    def _create_socket(self) -> None:
        logging.info(
            "Starting ssh mock server on %s:%s", self.host, self._port
        )
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self._port))
        self._socket.listen(5)

    def run_blocking(self) -> None:
        self._create_socket()
        self._run()

    def _run(self) -> None:
        assert self._socket is not None
        sock = self._socket
        selector = selectors.DefaultSelector()
        selector.register(sock, selectors.EVENT_READ)
        while sock.fileno() > 0:
            events = selector.select(timeout=1.0)
            if not events:
                continue
            try:
                conn, addr = sock.accept()
            except OSError as ex:
                if ex.errno in (errno.EBADF, errno.EINVAL):
                    break
                raise
            logging.debug("... got connection %s from %s", conn, addr)
            handler = ConnectionHandler(
                conn,
                self.inital_state,
                self._command_handler,
                self._default_line_ending,
            )
            thread = threading.Thread(target=handler.run)
            thread.daemon = True
            thread.start()

    def close(self) -> None:
        logging.debug("closing...")
        if self._socket:
            with suppress(Exception):
                self._socket.shutdown(socket.SHUT_RDWR)
            with suppress(Exception):
                self._socket.close()
            self._socket = None
