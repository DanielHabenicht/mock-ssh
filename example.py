from typing import Optional
from fake_ssh import Server
import logging

logging.basicConfig(level=logging.INFO)


def handler(command: str) -> Optional[str]:
    if command.startswith("ls"):
        return "file1\r\nfile2\r\n"
    elif command.startswith("echo"):
        return command[4:].strip() + "\r\n"

if __name__ == "__main__":
    Server(command_handler=handler, port=5050).run_blocking()