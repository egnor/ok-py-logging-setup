import logging
import typing


def exit(msg: str, *args, code: int = 1, **kw) -> typing.NoReturn:
    """
    Log a critical error (no stack) with the root logger, then exit the process.
    Typically used as a convenient error-and-exit for CLI utilities.
    """

    logging.critical(msg, *args, **kw)
    raise SystemExit(code)
