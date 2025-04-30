# ok-py-logging-setup

Simple, very opinionated [Python logging](https://docs.python.org/3/library/logging.html) setup with env-var configuration, logspam protection and minimalist formatting.

You probably won't want to use this. You should consider these libraries instead:
- [structlog](https://www.structlog.org/) - fancy logging system with interconnects to Python logging
- [Rich](https://github.com/Textualize/rich#readme) - pretty text formatter, includes a logging prettifier
- [Pretty Pie Log](https://github.com/chanpreet3000/pretty-pie-log) - logging prettifier

## Cantankerous opinion-ifesto

Python's standard logging facility is usable enough but (over)complicated with a tree of loggers with attached handlers, formatters, and filters configured in app code. There is an [external configuration system](https://docs.python.org/latest/library/logging.config.html) with ini-files and/or a custom socket protocol (!) that can customize that whole tree of loggers, handlers, formatters, and filters.

Modern [12-factor-ish apps](https://12factor.net/) don't want most of this. Logging should just go to stderr in some reasonable format; the app runner (Docker, systemd, etc) takes it from there. We just want an easy way to dial verbosity up and down for the app or subsystems depending on what we're debugging. That's what this library does (plus a few other tweaks I like).

Also, most logging formatters spend too much real estate on log levels, source locations, full timestamps, and other metadata. Better to leave space for the actual message, you can always search the code to find where it comes from.

## App code

Add this package as a dependency:
- `pip install ok-py-logging-setup`
- OR just copy `ok_logging_setup.py` (it has no dependencies)

Import the module and call `ok_logging_setup.install()` near program start:
```
import ok_logging_setup
...
def main():
    ok_logging_setup.install()
    ... run your app ...
```

This does the following:
- installs one stderr logger via [`logging.basicConfig`](https://docs.python.org/3/library/logging.html#logging.basicConfig), with log level INFO to start
- interprets `$OK_LOGGING_*` environment variables (described below)
- adds a formatter with minimal, legible output (described below)
- adds a filter with simple logspam-protection (described below)
- adds uncaught exception handlers that uses this logger (and exits)
- changes `sys.stdout` to line buffered, so `print` and logs interleave correctly
- resets control-C handling (`SIGINT`) to insta-kill (`SIG_DFL`), not Python's `InterruptException` nonsense

Then you can go ahead and use standard `logging` as usual, calling `.info`, `.error`, etc methods. You can call these functions on the `logger` module itself, or if you're feeling fancy create per-subsystem `Logger` objects so log messages are tagged for filtering convenience via `$OK_LOGGING_LEVEL` (see below).

Advanced options:
- pass a string-string dict to `ok_logging_setup.install` to set defaults for the environment variables below
- call `ok_logging_setup.skip_traceback_for(SomeClass)` to not print stack traces for exceptions of that type

## Configuration

### `$OK_LOGGING_LEVEL`

- set to a log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) to only print messages of that severity or higher
- use `loggertag=severity` to set the log level for a specific logger tag, eg. `my.library=DEBUG`
- combine the above with commas, eg. `WARNING,my.library=DEBUG,noisy.library=CRITICAL`

The most specific matching rule will apply to any given message, eg. in the last example above a logger named `noisy.library.submodule` would only print `CRITICAL` messages.

### `$OK_LOGGING_REPEAT_PER_MINUTE`

### `$OK_LOGGING_TIME_FORMAT` and `$OK_LOGGING_TIMEZONE`

## Log format

By default, log messages include a severity icon (emoji) and the message:
```
🕸 This is a debug message
This is an INFO message
⚠️ This is a WARNING message    
🔥 This is an ERROR message
💥 This is a CRITICAL message
```

If the message is logged with a named `Logger` object, the name is added as a prefix:
```
🔥 foo: This is an error message reported with a Logger named "foo"
```

If the message is logged from a named thread or a named asyncio task, the name is included
```
🔥 <Thread Name> This is an error message in a thread
🔥 [Task Name] This is an error message in a task
```

If you want timestamps, set `$OK_LOGGING_TIME_FORMAT` to a [`strftime` format](https://docs.python.org/3/library/datetime.html#format-codes) of your choice:
```
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
