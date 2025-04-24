"""
A log formatter to provide prettier output for messages from logging.error()
and friends, plus antispam measures. Automatically activated by import.
"""

import logging
import os
import re
import sys
import threading
import time

_max_per_minute = 10  # per message text

def config(level=logging.INFO, max_per_minute=10):
    global _max_per_minute
    _max_per_minute = max_per_minute
    logging.getLogger().setLevel(level)


class _LogFormatter(logging.Formatter):
    def format(self, record):
        m = record.getMessage()
        ml = m.lstrip()
        out = ml.rstrip()
        pre, post = m[: len(m) - len(ml)], ml[len(out) :]
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
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            out = f"{out.strip()}\n{record.exc_text}"
        if record.stack_info:
            out = f"{out.strip()}\n{record.stack_info}"
        return pre + out.strip() + post


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

        sig = _LogFilter.DIGITS.sub("#", str(record.msg))
        count = self._recently_seen.get(sig, 0)
        if count < 0:
            self._recently_seen[sig] = count  # Changed this line
            return False  # already suppressed
        elif _max_per_minute <= 0:
            return True  # suppression disabled
        elif count < _max_per_minute:
            self._recently_seen[sig] = count + 1
            return True
        else:
            self._recently_seen[sig] = -1  # suppressed until minute tick
            until = time.localtime((minute + 1) * 60)
            old_message = record.getMessage()
            record.msg = "%s [suppressing until %02d:%02d]"
            record.args = (old_message, until.tm_hour, until.tm_min)
            return True


def _sys_exception_hook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        logging.critical("*** KeyboardInterrupt (^C)! ***")
    else:
        exc_info = (exc_type, exc_value, exc_tb)
        logging.critical("Uncaught exception", exc_info=exc_info)
    os._exit(-1)  # pylint: disable=protected-access


def _thread_exception_hook(args):
    exc_info = (args.exc_type, args.exc_value, args.exc_traceback)
    logging.critical(
        'Uncaught exception in thread "%s"', args.thread.name, exc_info=exc_info
    )
    os._exit(-1)  # pylint: disable=protected-access


# Initialize on import.
_log_handler = logging.StreamHandler(stream=sys.stderr)
_log_handler.setFormatter(_LogFormatter())
_log_handler.addFilter(_LogFilter())
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
sys.excepthook = _sys_exception_hook
threading.excepthook = _thread_exception_hook
sys.stdout.reconfigure(line_buffering=True)  # log prints immediately
