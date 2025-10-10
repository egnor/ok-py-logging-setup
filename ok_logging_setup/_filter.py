"""LogFilter installed by ok_logging_setup.install()"""

import datetime
import logging
import re

import ok_logging_setup._formatter

repeat_per_minute = 10  # max per message 'signature' (format minus digits)


class LogFilter(logging.Filter):
    DIGITS = re.compile("[0-9]+")

    def __init__(self):
        super().__init__()
        self._last_minute = 0
        self._recently_seen = {}

    def filter(self, record: logging.LogRecord):
        minute = record.created // 60
        if minute != self._last_minute:
            self._recently_seen.clear()
            self._last_minute = minute

        if repeat_per_minute <= 0:
            return True  # suppression disabled

        sig = tuple(
            LogFilter.DIGITS.sub("#", s)
            for s in [record.msg, *record.args]
            if isinstance(s, str)
        ) or LogFilter.DIGITS.sub("#", record.getMessage())

        count = self._recently_seen.get(sig, 0)
        if count < 0:
            return False  # already suppressed
        elif count < repeat_per_minute:
            self._recently_seen[sig] = count + 1
            return True
        else:
            self._recently_seen[sig] = -1  # suppressed until minute tick
            until_sec = (minute + 1) * 60
            until_tz = ok_logging_setup._formatter.log_timezone
            until_dt = datetime.datetime.fromtimestamp(until_sec, until_tz)
            old_message = record.getMessage()
            record.msg = "%s [suppressing until %02d:%02d]"
            record.args = (old_message, until_dt.hour, until_dt.minute)
            return True
