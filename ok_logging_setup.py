"""
A log formatter to provide prettier output for messages from logging.error()
and friends, plus anti-logspam measures and various sane defaults.

Activated with ok_logging_setup.install().
"""

import datetime
import logging
import os
import re
import signal
import sys
import threading
import zoneinfo

ENV_LEVEL_RE = re.compile(r"(?i)\s*((?P<module>[\w.]+)\s*=)?\s*(?P<level>\w+)")
TASK_IGNORE_RE = re.compile(r"(|Task-\d+)")
THREAD_IGNORE_RE = re.compile(r"(|MainThread|Thread-\d+)")

_logger = logging.getLogger(__name__)  # very meta
_repeat_per_minute = 10  # max per message 'signature' (format minus digits)
_skip_traceback_for = ()
_time_format = ""
_timezone = None


def install(*, env_defaults={}):
    if logging.root.handlers:
        raise RuntimeError(f"ok_logging_setup install after logging configured")

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # sane ^C handling by default

    log_handler = logging.StreamHandler(stream=sys.stderr)
    log_handler.setFormatter(_LogFormatter())
    log_handler.addFilter(_LogFilter())
    logging.basicConfig(level=logging.INFO, handlers=[log_handler])

    sys.excepthook = _sys_exception_hook
    sys.unraisablehook = _sys_unraisable_hook
    threading.excepthook = _thread_exception_hook
    sys.stdout.reconfigure(line_buffering=True)  # log prints immediately
    _configure({**env_defaults, **os.environ})


def skip_traceback_for(klass):
    if not issubclass(klass, BaseException):
        raise TypeError(f"Bad skip_traceback_for value {klass!r}")

    global _skip_traceback_for
    if not issubclass(klass, _skip_traceback_for):
        _skip_traceback_for += (klass,)


class _LogFormatter(logging.Formatter):
    def format(self, record):
        m = record.getMessage()
        ml = m.lstrip()
        out = ml.rstrip()
        pre, post = m[: len(m) - len(ml)], ml[len(out) :]
        if not THREAD_IGNORE_RE.fullmatch(record.threadName or ""):
            out = f"<{record.threadName}> {out}"
        if not TASK_IGNORE_RE.fullmatch(record.taskName or ""):
            out = f"[{record.taskName}] {out}"
        if record.name != "root":
            out = f"{record.name}: {out}"
        if record.levelno < logging.INFO:
            out = f"🕸  {out}"
        elif record.levelno >= logging.CRITICAL:
            out = f"💥 {out}"
        elif record.levelno >= logging.ERROR:
            out = f"🔥 {out}"
        elif record.levelno >= logging.WARNING:
            out = f"⚠️ {out}"
        if _time_format:
            dt = datetime.datetime.fromtimestamp(record.created, _timezone)
            out = f"{dt.strftime(_time_format)} {out}"
        if record.exc_info:
            if issubclass(record.exc_info[0], _skip_traceback_for):
                record.exc_info = record.exc_info[:2] + (None,)
                record.stack_info = None
            out = f"{out.rstrip()}\n{self.formatException(record.exc_info)}"
            if record.stack_info:
                out = f"{out.rstrip()}\nStack:\n{record.stack_info}"
        return pre + out.strip() + post


def _configure(env):
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
            _repeat_per_minute = int(env_repeat)
        except ValueError:
            _logger.warning(f'Bad $OK_LOGGING_REPEAT_PER_MINUTE "{env_repeat}"')

    global _time_format, _timezone
    if _time_format := env.pop("OK_LOGGING_TIME_FORMAT", ""):
        if env_timezone := env.pop("OK_LOGGING_TIMEZONE", ""):
            try:
                _timezone = zoneinfo.ZoneInfo(env_timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                _logger.warning(f'Bad $OK_LOGGING_TIMEZONE "{env_timezone}"')

    for key, value in env.items():
        if key.upper().startswith("OK_LOGGING") and value:
            _logger.warning("Unknown variable $%s=%s", key, value)


class _LogFilter(logging.Filter):
    DIGITS = re.compile("[0-9]+")

    def __init__(self):
        super().__init__()
        self._last_minute = 0
        self._recently_seen = {}

    def filter(self, record):
        minute = record.created // 60
        if minute != self._last_minute:
            self._recently_seen.clear()
            self._last_minute = minute

        if _repeat_per_minute <= 0:
            return True  # suppression disabled

        sig = _LogFilter.DIGITS.sub("#", str(record.msg))
        count = self._recently_seen.get(sig, 0)
        if count < 0:
            return False  # already suppressed
        elif count < _repeat_per_minute:
            self._recently_seen[sig] = count + 1
            return True
        else:
            self._recently_seen[sig] = -1  # suppressed until minute tick
            until_sec = (minute + 1) * 60
            until_dt = datetime.datetime.fromtimestamp(until_sec, _timezone)
            old_message = record.getMessage()
            record.msg = "%s [suppressing until %02d:%02d]"
            record.args = (old_message, until_dt.hour, until_dt.minute)
            return True


def _sys_exception_hook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        logging.critical("\n🛑 KeyboardInterrupt (^C)! 🛑 💥")
    else:
        exc_info = (exc_type, exc_value, exc_tb)
        logging.critical("Uncaught exception", exc_info=exc_info)
    os._exit(1)  # pylint: disable=protected-access


def _sys_unraisable_hook(unr):
    if unr.err_msg:
        logging.warning("%s: %s", unr.err_msg, repr(unr.object))
    else:
        exc_info = (unr.exc_type, unr.exc_value, unr.exc_traceback)
        logging.critical("Uncatchable exception", exc_info=exc_info)
    os._exit(1)  # pylint: disable=protected-access


def _thread_exception_hook(args):
    exc_info = (args.exc_type, args.exc_value, args.exc_traceback)
    logging.critical("Uncaught exception in thread", exc_info=exc_info)
    os._exit(1)  # pylint: disable=protected-access
