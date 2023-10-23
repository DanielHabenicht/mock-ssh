import contextlib

import logging

@contextlib.contextmanager
def suppress(exception: Exception):
    try:
        yield
    except exception as ex:
        logging.debug(f"Caught exception: {ex}")
