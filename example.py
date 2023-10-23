from typing import Optional
from ssh_mock import Server, CommandResult
import logging
import os

logging.basicConfig(level=logging.INFO)

# Read HOST and PORT from ENV
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5050"))
DEFAULT_HOST = os.getenv("DEFAULT_HOST", "SSHMOCK>")


def handler(command: str) -> Optional[str]:
    pass


if __name__ == "__main__":
    Server(
        # Read from ENV
        host=HOST,
        port=PORT,
        default_host=DEFAULT_HOST,
        command_handler=handler,
        commands_file="commands.yml",
    ).run_blocking()
