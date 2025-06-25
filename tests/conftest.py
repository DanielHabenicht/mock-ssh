import threading
import pytest

from ssh_mock import Server


@pytest.fixture(scope="session")
def server():
    def run_server():
        def handler(command: str, state) -> str:
            if command == "ls":
                return "file1\nfile2"
            elif command.startswith("echo"):
                return command[4:].strip()
            return None
        mock_server = Server(command_handler=handler, port=5050)
        mock_server.run_blocking()
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    yield "127.0.0.1:5050"
    # thread.join()
