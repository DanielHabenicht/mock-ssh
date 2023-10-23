import os
import socket
import threading
from queue import Queue
from typing import Dict, Optional

import paramiko
import logging

from .command import CommandHandler

ChannelID = int
_SERVER_KEY = os.path.join(os.path.dirname(__file__), "server_key")
EOL = "\r\n"


class ConnectionHandler(paramiko.ServerInterface):
    def __init__(
        self, client_conn: socket.SocketIO, command_handler: CommandHandler
    ):
        self._command_handler: CommandHandler = command_handler
        self.thread: Optional[threading.Thread] = None
        self.command_queues: Dict[ChannelID, Queue] = {}
        self.transport: paramiko.Transport = paramiko.Transport(client_conn)
        self.transport.add_server_key(paramiko.RSAKey(filename=_SERVER_KEY))

    def run(self) -> None:
        self.transport.start_server(server=self)
        while True:
            channel: paramiko.Channel = self.transport.accept()
            if channel is None:
                logging.debug("Closing session")
                break

            func = self._handle_client
            if channel.chanid not in self.command_queues:
                func = self._handle_interactive_client
            
            
            thread = threading.Thread(
                target=func, args=(channel,)
            )
            thread.setDaemon(True)
            thread.start()

    def _handle_client(self, channel: paramiko.Channel) -> None:
        try:
            logging.error(f"Hi")
            channel.sendall("Hello# ")

            command = self.command_queues[channel.chanid].get(block=True)
            logging.debug(f"Channel {channel.chanid}, executing {command}")
            command_result = self._command_handler(command.decode())
            
            channel.sendall(command_result.stdout)
            channel.sendall_stderr(command_result.stderr)
            channel.send_exit_status(command_result.returncode)

        except Exception:  # pylint: disable=broad-except
            logging.exception(f"Error handling client (channel: {channel})")
        finally:
            try:
                channel.close()
            except EOFError:
                logging.debug("Tried to close already closed channel")
    
    def _handle_interactive_client(self, channel: paramiko.Channel) -> None:
        try:
            # Read input line by line or when escape character is pressed
            while True:
                channel.sendall("Hello#" + EOL)
                
                current_line = b""
                while True:
                    char = channel.recv(1)
                    current_line += char
                    if char == b'\x03':
                        return
                    channel.sendall(char)
                    if char == b'\r' or char == b'\n':
                        break
                
                channel.sendall("\n")
                command = current_line
                
                
                logging.info("Received Command: %s", command)
                
                command_result = self._command_handler(command.decode())
                
                logging.info("Send Answer: %s", command_result.stdout)
                if (command_result.found):                
                    channel.sendall(command_result.stdout)
                    channel.sendall_stderr(command_result.stderr)
                    channel.send_exit_status(command_result.returncode)
                else:
                    logging.info("Command '%s' not found!", command)
                    channel.sendall_stderr("#MOCKSERVERFAILURE# Command not found\r\n")
                    channel.send_exit_status(1)

        except Exception:  # pylint: disable=broad-except
            logging.exception("Error handling client (channel: %s)", channel)
        finally:
            try:
                channel.close()
            except EOFError:
                logging.debug("Tried to close already closed channel")

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username: str, password: str) -> int:
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_none(self, username) -> int:
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_exec_request(
        self, channel: paramiko.Channel, command: bytes
    ) -> bool:
        self.command_queues.setdefault(channel.get_id(), Queue()).put(command)
        return True

    def check_channel_pty_request(
        self, channel: paramiko.Channel, term: str, width: int, height: int, pixelwidth: int, pixelheight: int, modes) -> bool:
        return True

    def check_channel_shell_request(
        self, channel: paramiko.Channel) -> bool:
        return True

    def check_channel_request(self, kind: str, chanid: ChannelID) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username: str) -> str:
        return "password,publickey"
