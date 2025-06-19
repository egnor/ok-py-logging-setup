"""LogFormatter installed by ok_logging_setup.install()"""

import datetime
import logging
import re
import typing
import unicodedata

TASK_IGNORE_RE = re.compile(r"(|Task-\d+)")
THREAD_IGNORE_RE = re.compile(r"(|MainThread|Thread-\d+)")

skip_traceback_types: tuple[typing.Type[BaseException], ...] = ()
log_time_format = ""
log_timezone = None


class LogFormatter(logging.Formatter):
    def format(self, rec: logging.LogRecord):
        m = rec.getMessage()
        ml = m.lstrip()
        out = ml.rstrip()
        pre, post = m[: len(m) - len(ml)], ml[len(out) :]
        if not THREAD_IGNORE_RE.fullmatch(rec.threadName or ""):
            out = f"<{rec.threadName}> {out}"
        if not TASK_IGNORE_RE.fullmatch(getattr(rec, "taskName", "") or ""):
            out = f"[{getattr(rec, 'taskName')}] {out}"
        if rec.name != "root":
            out = f"{rec.name}: {out}"
        if rec.levelno < logging.INFO:
            out = f"🕸  {out}"  # skip _starts_with_emoji for performance?
        elif rec.levelno >= logging.CRITICAL:
            if not _starts_with_emoji(out):
                out = f"💥 {out}"
        elif rec.levelno >= logging.ERROR:
            if not _starts_with_emoji(out):
                out = f"🔥 {out}"
        elif rec.levelno >= logging.WARNING:
            if not _starts_with_emoji(out):
                out = f"⚠️ {out}"

        if log_time_format:
            dt = datetime.datetime.fromtimestamp(rec.created, log_timezone)
            out = f"{dt.strftime(log_time_format)} {out}"

        exc, stack = rec.exc_info, rec.stack_info
        if exc and exc[0] and issubclass(exc[0], skip_traceback_types):
            exc = (exc[0], exc[1], None)
            stack = None
        if exc:
            out = f"{out.rstrip()}\n{self.formatException(exc)}"
        if stack:
            out = f"{out.rstrip()}\nStack:\n{stack}"
        return pre + out.strip() + post


def skip_traceback_for(klass: typing.Type[BaseException]):
    """
    Add to the list of exception classes where tracebacks are suppressed
    in regular logging or when handling uncaught exceptions. Good for
    exceptions with self-evident causes where stack traces are noise.
    """

    if not issubclass(klass, BaseException):
        raise TypeError(f"Bad skip_traceback_for value {klass!r}")

    global skip_traceback_types
    if not issubclass(klass, skip_traceback_types):
        skip_traceback_types += (klass,)


def _starts_with_emoji(str):
    return unicodedata.category(str[:1]) == "So"
