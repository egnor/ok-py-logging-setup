"""Implementation of ok_logging_setup.install() (exposed by __init__.py)"""

import io
import logging
import os
import re
import signal
import sys
import threading
import typing
import unicodedata
import zoneinfo

import ok_logging_setup._filter
import ok_logging_setup._formatter

ENV_LEVEL_RE = re.compile(r"(?i)\s*((?P<module>[\w.]+)\s*=)?\s*(?P<level>\w+)")

_logger = logging.getLogger(__name__)  # very meta

_handler = None


def install(env_defaults: typing.Dict[str, str]={}):
    """
    Sets up Python logging the ok_logging_setup way. Must be called without
    any other logging handlers added. See README.md for full documentation.

    :param env_defaults: Default environment variables for configuration.
    """

    global _handler
    if logging.root.handlers:
        if logging.root.handlers[0] is _handler: return
        raise RuntimeError("ok_logging_setup.install() with logging configured")

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, signal.SIG_DFL)  # sane ^C handling

    _handler = logging.StreamHandler(stream=sys.stderr)
    _handler.setFormatter(ok_logging_setup._formatter.LogFormatter())
    _handler.addFilter(ok_logging_setup._filter.LogFilter())
    logging.basicConfig(level=logging.INFO, handlers=[_handler])
    sys.excepthook = _sys_exception_hook
    sys.unraisablehook = _sys_unraisable_hook
    threading.excepthook = _thread_exception_hook
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)  # print immediately
    _configure({**env_defaults, **os.environ})

def exit(msg: str, *args, code: int=1, **kw):
    """
    Log a critical error (no stack) with the root logger, then exit the process.
    Typically used as a convenient error-and-exit for CLI utilities.
    """

    logging.critical(msg, *args, **kw)
    raise SystemExit(code)


def _configure(env):
    if stream := env.pop("OK_LOGGING_OUTPUT", ""):
        if stream == "stdout":
            _handler.setStream(sys.stdout)
        elif stream == "stderr":
            _handler.setStream(sys.stderr)
        else:
            _logger.warning(f'Bad $OK_LOGGING_OUTPUT "{stream}"')

    for env_level in env.pop("OK_LOGGING_LEVEL", "").split(","):
        if env_match := ENV_LEVEL_RE.fullmatch(env_level):
            module = env_match.group("module")
            level = env_match.group("level").upper()
            logger = logging.getLogger(module) if module else logging.root
            try:
                logger.setLevel(level)
            except ValueError:
                _logger.warning(f'Bad $OK_LOGGING_LEVEL level "{level}"')
        elif env_level.strip():
            _logger.warning(f'Bad $OK_LOGGING_LEVEL entry "{env_level}"')

    if env_repeat := env.pop("OK_LOGGING_REPEAT_PER_MINUTE", ""):
        try:
            ok_logging_setup._filter.repeat_per_minute = int(env_repeat)
        except ValueError:
            _logger.warning(f'Bad $OK_LOGGING_REPEAT_PER_MINUTE "{env_repeat}"')

    if env_time_format := env.pop("OK_LOGGING_TIME_FORMAT", ""):
        ok_logging_setup._formatter.log_time_format = env_time_format
        if env_timezone := env.pop("OK_LOGGING_TIMEZONE", ""):
            try:
                timezone = zoneinfo.ZoneInfo(env_timezone)
                ok_logging_setup._formatter.log_timezone = timezone
            except zoneinfo.ZoneInfoNotFoundError:
                _logger.warning(f'Bad $OK_LOGGING_TIMEZONE "{env_timezone}"')

    for key, value in env.items():
        if key.upper().startswith("OK_LOGGING") and value:
            _logger.warning("Unknown variable $%s=%s", key, value)


def _starts_with_emoji(str):
    return unicodedata.category(str[:1]) == "So"


def _sys_exception_hook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        logging.critical("\n❌ KeyboardInterrupt (^C)! ❌")
    else:
        exc_info = (exc_type, exc_value, exc_tb)
        logging.critical("Uncaught exception", exc_info=exc_info)

    # after return, the python runtime will execute atexit handlers and exit


def _sys_unraisable_hook(unr):
    if unr.err_msg:
        logging.critical("%s: %s", unr.err_msg, repr(unr.object))
    else:
        exc_info = (unr.exc_type, unr.exc_value, unr.exc_traceback)
        logging.critical("Uncatchable exception", exc_info=exc_info)

    # the python runtime would continue, instead exit the program by policy
    # (this does unfortunately bypass atexit handlers)
    os._exit(1)  # pylint: disable=protected-access


def _thread_exception_hook(args):
    exc_info = (args.exc_type, args.exc_value, args.exc_traceback)
    logging.critical("Uncaught exception in thread", exc_info=exc_info)

    # otehr threads would continue, instead exit the whole program by policy
    # (this does unfortunately bypass atexit handlers)
    os._exit(1)  # pylint: disable=protected-access
