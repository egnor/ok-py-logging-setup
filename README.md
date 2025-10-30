# ok-logging-setup for Python

Simple, opinionated [Python logging](https://docs.python.org/3/library/logging.html) setup with env-var configuration, logspam limiting and minimalist formatting.

You probably won't want to use this. You should consider these libraries instead:
- [structlog](https://www.structlog.org/) - fancy logging system with interconnects to Python logging
- [Rich](https://github.com/Textualize/rich#readme) - pretty text formatter, includes a logging prettifier
- [Pretty Pie Log](https://github.com/chanpreet3000/pretty-pie-log) - logging prettifier
- [logging518](https://github.com/mharrisb1/logging518) - configure logging in pyproject.toml (or another TOML file)
- [Easy Logging](https://github.com/Kiennguyen08/easy-logging-setup) - logging setup with YAML configuration
- [simple-logging-setup](https://github.com/fscherf/simple-logging-setup) - a colorful take on logging defaults
- [setup logging for me](https://github.com/jmansilla/setup_logging_for_me) - even more minimal and idiosyncratic than this package!

## Opinion-ifesto

Python's `logging` module is usable enough but (over)complicated with a tree of loggers with attached handlers, formatters, and filters, plus similarly (over)complicated [external configuration](https://docs.python.org/latest/library/logging.config.html) using ini-files and/or a custom socket protocol (!) to customize that whole mess.

Modern [12-factor-ish apps](https://12factor.net/) don't want most of this. Logging should just go to stderr in some reasonable format; the app runner (Docker, systemd, etc) takes it from there. I just need an environment variable to dial verbosity up and down for the app or subsystems I'm debugging. That's what this library offers.

Also, most logging formatters spend too much real estate on log levels, source locations, full timestamps, and other metadata. This library adds a minimalist formatter that skips most of that (see below). You can always search the code to find a message's origin! (Stack traces are still printed for exceptions.)

## Usage

Add this package as a dependency:
- `pip install ok-logging-setup`
- OR just copy the `ok_logging_setup/` dir (it has no dependencies)

Import the module and call `ok_logging_setup.install()` near program start:
```python
import ok_logging_setup
...
def main():
    ok_logging_setup.install()
    ... run your app ...
```

The `ok_logging_setup.install()` call does the following:
- makes a root stderr logger via [`logging.basicConfig`](https://docs.python.org/3/library/logging.html#logging.basicConfig), with log level INFO to start
- interprets `$OK_LOGGING_*` environment variables (described below)
- adds a formatter with minimal, legible output (described below)
- adds a filter with simple logspam-protection (described below)
- adds an uncaught exception handler that uses this logger
- adds a thread exception handler that uses this logger *and exits*
- adds an "unraisable" exception handler that uses this logger *and exits*
- changes `sys.stdout` to line buffered, so `print` and logs interleave correctly
- resets control-C handling (`SIGINT`) to insta-kill (`SIG_DFL`), not Python's `InterruptException` nonsense

Advanced usage:
- pass a string-string dict to `ok_logging_setup.install({ ... })` to set defaults (see below)
- call `ok_logging_setup.exit(msg, ...)` to log a `.critical(msg, ...)` and immediately `sys.exit(1)`
- call `ok_logging_setup.skip_traceback_for(SomeClass)` to not print stacks for that exception

After installation, use `.info`, `.error`, etc as normal on the `logger` module itself, or if you're fancy, use per-subsystem `Logger` objects to log messages for selective filtering (see `$OK_LOGGING_LEVEL` below).

## Configuration

These variables can be set in the environment, or passed in a dict to `ok_logging_setup.install({ ... })` (the environment takes precedence).

### `$OK_LOGGING_LEVEL` (default `INFO`)

- set to a log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) to only print messages of that severity or higher
- use `loggertag=severity` to set the log level for a specific logger tag, eg. `my.library=DEBUG`
- combine the above with commas, eg. `WARNING,my.library=DEBUG,noisy.library=CRITICAL`

The most specific matching rule will apply to any given message, eg. in the last example above a logger named `noisy.library.submodule` would only print `CRITICAL` messages.

### `$OK_LOGGING_OUTPUT` (default `stderr`)

Set this to `stderr` or `stdout` and logs will be written to that stream.

### `$OK_LOGGING_REPEAT_PER_MINUTE` (default 10)

The number of messages with the same "signature" (format and string args, with digits removed) allowed in one minute before being blocked by spam protection (see below). Set to `0` to disable the spam filter entirely.

### `$OK_LOGGING_TIME_FORMAT` and `$OK_LOGGING_TIMEZONE`

- to timestamp log messages, set `$OK_LOGGING_TIME_FORMAT` to a [`strftime` format](https://docs.python.org/3/library/datetime.html#format-codes)
- if set, `$OK_LOGGING_TIMEZONE` ([from this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) is used for timestamps

## Spam protection

If logs get emitted in a tight loop somehow, it can slow code down, fill up disks, and generally make a bad day. To mitigate spam, `ok_logging_setup.install` adds a filter that checks if a log message with the same "signature" (format string with digits removed) more than N times in a one minute period, subsequent instances of that same "signature" are dropped until the minute rolls over. It looks like this:

```
12:34:00 Spam message 1
12:34:01 Spam message 2
12:34:02 Spam message 3
12:34:03 Spam message 4
12:34:04 Spam message 5
12:34:05 Spam message 6
12:34:06 Spam message 7
12:34:07 Spam message 8
12:34:08 Spam message 9
12:34:09 Spam message 10
12:34:10 Spam message 11 [suppressing until 12:35]
12:35:00 Spam message 61
12:35:01 Spam message 62
12:35:02 Spam message 63
12:35:03 Spam message 64
12:35:04 Spam message 65
12:35:05 Spam message 66
12:35:06 Spam message 67
12:35:07 Spam message 68
12:35:08 Spam message 69
12:35:09 Spam message 70
12:35:10 Spam message 71 [suppressing until 12:36]
12:36:00 Spam message 121
12:36:01 Spam message 122
...
```

The "suppressing until ..." messages are appended so you know when log messages are potentially skipped. Spam filtering can be tuned by setting `$OK_LOGGING_REPEAT_PER_MINUTE` to the maximum number of messages with the same signature to allow per minute, or `0` to disable the filter entirely.

## Log format

By default, log messages include a severity icon (emoji) and the message:
```
🕸 This is a debug message
This is an INFO message
⚠️ This is a WARNING message    
🔥 This is an ERROR message
💥 This is a CRITICAL message
```

(If the message already starts with an emoji, no emoji prefix is added; your emoji is assumed to convey appropriate importance.)

If the message is logged with a named `Logger` object, the name is added as a prefix:
```
🔥 foo: This is an error message reported with a Logger named "foo"
```

If the message is logged from a named thread or a named asyncio task, the name is included
```
🔥 <Thread Name> This is an error message in a thread
🔥 [Task Name] This is an error message in a task
```

If you want timestamps, set `$OK_LOGGING_TIME_FORMAT` (see above):
```bash
$ export OK_LOGGING_TIME_FORMAT="%m-%d %H:%M:%S"
...
04-30 22:53:26 🔥 This is an error message
```

Exceptions are formatted in the normal way:
```
💥 Uncaught exception
Traceback (most recent call last):
  File "/home/egnor/source/ok-py-logging-setup/try_ok_logging_setup.py", line 109, in <module>
    main()
  File "/home/egnor/source/ok-py-logging-setup/try_ok_logging_setup.py", line 55, in main
    raise Exception("This is an uncaught exception")
Exception: This is an uncaught exception
```
