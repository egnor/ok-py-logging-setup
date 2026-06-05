"""LogFormatter installed by ok_logging_setup.install()"""

import builtins
import copy
import datetime
import logging
import re
import typing
import unicodedata

TASK_IGNORE_RE = re.compile(r"(|Task-\d+)")
THREAD_IGNORE_RE = re.compile(r"(|MainThread|Thread-\d+)")
TIME_FRACTION_RE = re.compile(r"%\.?([1-6])f")

log_prefix = ""
log_terminator = "\n"
log_time_format = ""
log_timezone = None

skip_traceback_types: tuple[typing.Type[BaseException], ...] = ()

base_exception_group_type = getattr(builtins, "BaseExceptionGroup", None)


class LogFormatter(logging.Formatter):
    def format(self, rec: logging.LogRecord):
        m = rec.getMessage()
        ml = m.lstrip()
        out = ml.rstrip()
        pre_space, post_space = m[: len(m) - len(ml)], ml[len(out) :]
        if not THREAD_IGNORE_RE.fullmatch(rec.threadName or ""):
            out = f"<{rec.threadName}> {out}"
        if not TASK_IGNORE_RE.fullmatch(getattr(rec, "taskName", "") or ""):
            out = f"[{getattr(rec, 'taskName')}] {out}"
        if rec.name != "root":
            out = f"{rec.name}: {out}"
        if rec.levelno <= logging.DEBUG:
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
            format = TIME_FRACTION_RE.sub(
                lambda m: f"{dt.microsecond:06d}"[: int(m.group(1) or "6")],
                log_time_format,
            )
            out = f"{dt.strftime(format)} {out}"

        einfo, stack = rec.exc_info, rec.stack_info
        if einfo and einfo[1]:
            if new_ex := _simplify_exception(einfo[1]):
                einfo = (type(new_ex), new_ex, new_ex.__traceback__)
            out = f"{out.rstrip()}\n{self.formatException(einfo)}"

        if stack:
            out = f"{out.rstrip()}\nStack:\n{stack}"

        assembled = pre_space + log_prefix + out.strip() + post_space
        if log_terminator != "\n":
            assembled = assembled.replace("\n", log_terminator)
        return assembled


def skip_traceback_for(klass: typing.Type[BaseException]):
    """
    Adds an exception class to the list where stack tracebacks are skipped
    in regular logging or when handling uncaught exceptions. Good for
    exceptions with self-evident causes where stack traces are noise.
    """

    if not issubclass(klass, BaseException):
        raise TypeError(f"Bad skip_traceback_for value {klass!r}")

    global skip_traceback_types
    if not issubclass(klass, skip_traceback_types):
        skip_traceback_types += (klass,)


def _simplify_exception(exc: BaseException | None) -> BaseException | None:
    """Returns a simplified copy for printing, None if no changes needed."""

    if not exc:
        return exc

    new_exc: BaseException | None = None
    if base_exception_group_type and isinstance(exc, base_exception_group_type):
        contained = exc.exceptions  # type: ignore[attr-defined]
        new_contained = tuple([_simplify_exception(e) or e for e in contained])
        if len(new_contained) == 1:
            return new_contained[0]
        if new_contained != contained:
            new_exc = exc.derive(new_contained)  # type: ignore[attr-defined]
            new_exc.__cause__ = exc.__cause__
            new_exc.__context__ = exc.__context__
            if any(e.__traceback__ for e in new_contained):
                new_exc.__traceback__ = exc.__traceback__

    if isinstance(exc, skip_traceback_types):
        new_exc = new_exc or copy.copy(exc)
        new_exc.__traceback__ = None

    if new_cause := _simplify_exception(exc.__cause__):
        new_exc = new_exc or copy.copy(exc)
        new_exc.__cause__ = new_cause

    if not exc.__suppress_context__:
        if new_context := _simplify_exception(exc.__context__):
            new_exc = new_exc or copy.copy(exc)
            new_exc.__context__ = new_context

    return new_exc


def _starts_with_emoji(str):
    return unicodedata.category(str[:1]) == "So"
