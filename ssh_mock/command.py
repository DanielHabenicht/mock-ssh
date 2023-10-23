import functools
from dataclasses import dataclass, field
from typing import Callable, Optional, Union


@dataclass
class CommandResult:
    stdout: str = field(default="")
    stderr: str = field(default="")
    returncode: int = field(default=0)
    found: bool = field(default=False)


CommandHandlerResult = Optional[Union[CommandResult, str]]
CommandHandler = Callable[[str], CommandHandlerResult]
CommandHandlerWrapped = Callable[[str], CommandResult]


class CommandFailure(Exception):
    def __init__(self, stderr, returncode=1):
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(stderr)


def command_handler_wrapper(
    func: Callable[[str], Union[str, CommandResult]]
) -> CommandHandlerWrapped:
    @functools.wraps(func)
    def wrapped(command: str) -> CommandResult:
        try:
            result = func(command)
        except CommandFailure as ex:
            return CommandResult(stderr=ex.stderr, returncode=ex.returncode, found=True)
        except Exception as ex:  # pylint: disable=broad-except
            return CommandResult(stderr=str(ex), returncode=1, found=True)
        if isinstance(result, CommandResult):
            result.found = True
            return result
        if result is None:
            return CommandResult()
        if isinstance(result, str):
            return CommandResult(stdout=result)
        raise TypeError(
            f"Unknown type for result: {result}, type: {type(result)}"
        )

    return wrapped
