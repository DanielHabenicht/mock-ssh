import errno
import selectors
import socket
import threading
import logging
from typing import Any, Optional, Tuple

import re
import yaml
from jinja2 import Environment, BaseLoader

from .command import (
    CommandHandler,
    CommandHandlerResult,
    CommandHandlerWrapped,
    CommandResult,
    command_handler_wrapper,
)
from .connection_handler import ConnectionHandler
from .utils import suppress


def add_file_commands(
    commands_file: str, command_handler: CommandHandler
) -> CommandHandlerWrapped:
    with open(commands_file, "r", encoding="utf-8") as stream:
        try:
            commands = yaml.safe_load(stream)["commands"]
        except yaml.YAMLError as exc:
            logging.error(exc)
            raise

    def new_command_handler(command: str) -> CommandHandlerResult:
        res = command_handler(command)
        if res is not None:
            return res

        for cmd in commands:
            regex = re.compile(cmd["command"])
            if regex.match(command):
                result = CommandResult()
                if "stdout_template" in cmd:
                    template = Environment(loader=BaseLoader).from_string(
                        cmd["stdout_template"]
                    )
                    result.stdout = template.render(command=command)
                elif "stdout" in cmd:
                    result.stdout = cmd["stdout"]
                if "stderr" in cmd:
                    result.stderr = cmd["stderr"]
                if "returncode" in cmd:
                    result.returncode = cmd["returncode"]
                if "modify_host" in cmd:
                    result.modify_host = cmd["modify_host"]
                else:
                    result.returncode = 0
                return result
        return None

    return command_handler_wrapper(new_command_handler)


class Server:
    def __init__(
        self,
        command_handler: CommandHandler,
        commands_file: str = None,
        host: str = "127.0.0.1",
        port: int = 0,
        default_host: str = "SSHMOCK>",
    ):
        self._socket: Optional[socket.SocketIO] = None
        self._thread: Optional[threading.Thread] = None
        self.host: str = host
        self._port: int = port
        if commands_file is not None:
            self._command_handler = add_file_commands(
                commands_file=commands_file, command_handler=command_handler
            )
        else:
            self._command_handler: CommandHandlerWrapped = (
                command_handler_wrapper(command_handler)
            )

        self._default_host: str = default_host

    def __enter__(self) -> "Server":
        self.run_non_blocking()
        return self

    def run_non_blocking(self) -> None:
        self._create_socket()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

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
                conn, self._command_handler, self._default_host
            )
            thread = threading.Thread(target=handler.run)
            thread.daemon = True
            thread.start()

    def __exit__(self, *exc_info: Tuple[Any]) -> None:
        self.close()

    def close(self) -> None:
        logging.debug("closing...")
        if self._socket:
            with suppress(Exception):
                self._socket.shutdown(socket.SHUT_RDWR)
            with suppress(Exception):
                self._socket.close()
            self._socket = None
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    @property
    def port(self) -> int:
        if self._socket is None:
            raise RuntimeError("Server not running")
        return self._socket.getsockname()[1]
