"""LogFilter installed by ok_logging_setup.install()"""

import collections
import logging
import re

repeat_burst = 20  # max per message 'signature' (format minus digits)
repeat_delay = 1.0  # seconds per message when repeat_burst is hit


class LogFilter(logging.Filter):
    DIGITS = re.compile("[0-9]+")

    def __init__(self):
        super().__init__()
        self._allow_time: dict[tuple, float] = {}
        self._allow_max = 0.0
        self._prev_allow_time: dict[tuple, float] = {}
        self._prev_allow_max = 0.0

    def filter(self, record: logging.LogRecord):
        if (
            record.levelno <= logging.DEBUG
            or repeat_delay <= 0
            or getattr(record, "repeat_ok", False)
        ):
            return True  # suppression disabled

        sig = tuple(
            LogFilter.DIGITS.sub("#", s)
            for s in [record.msg, *(record.args or [])]
            if isinstance(s, str)
        ) or LogFilter.DIGITS.sub("#", record.getMessage())

        allow_time = self._allow_time.get(sig, 0.0)
        if allow_time > record.created:
            return False

        min_allow_time = record.created - repeat_delay * repeat_burst
        if self._prev_allow_max < min_allow_time:
            self._prev_allow_time = self._allow_time
            self._prev_allow_max = self._allow_max
            self._allow_time = {}
            self._allow_max = 0.0
        else:
            allow_time = max(allow_time, self._prev_allow_time.get(sig, 0.0))
            if allow_time > record.created:
                return False

        new_allow_time = max(allow_time, min_allow_time) + repeat_delay
        self._allow_time[sig] = new_allow_time
        self._allow_max = max(self._allow_max, new_allow_time)
        if new_allow_time > record.created:
            record.msg = f"{record.msg} [⏱️ ]"

        return True
