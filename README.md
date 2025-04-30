# ok-py-logging-setup

Simple, very opinionated [Python logging](https://docs.python.org/3/library/logging.html) defaults with rate limiting and minimalist formatting.

You probably won't want to use this. You should consider these libraries instead:
- [structlog](https://www.structlog.org/) - fancy logging system with interconnects to Python logging
- [Rich](https://github.com/Textualize/rich#readme) - pretty text formatter, includes a logging prettifier

## Cantankerous opinion-ifesto

Python's standard logging facility is usable enough but (over)complicated with a tree of loggers with attached handlers, formatters, and filters configured in app code. There is an [external configuration system](https://docs.python.org/latest/library/logging.config.html) with ini-files and/or a custom socket protocol (!) that can customize that whole tree of loggers, handlers, formatters, and filters. Modern [12-factor-ish apps](https://12factor.net/) don't want most of this. Logging should just go to stderr in some reasonable format, and the deployment system (Docker, systemd, etc) takes it from there. We just want a very simple way to dial verbosity up and down for the app or subsystems depending on what we're debugging.

Of course it's quite possible to use Python standard logging that way, and that's what this tiny library does based on very simple environment variable configuration. (It's logging _setup_, not a logging system.) It also sets some other logging-adjacent defaults I like.

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

This sets things up as follows:
- makes one stdout logger via [`logging.basicConfig`](https://docs.python.org/3/library/logging.html#logging.basicConfig), with log level INFO by default
- interprets `$OK_LOGGING_*` environment variables (described below)
- adds a formatter with minimal, legible output (described below)
- adds a filter with simple logspam-protection (described below)
- adds uncaught exception handlers that uses this logger (and exits)
- (etc: describe ^C handler, line buffering stdout)

Then you can go ahead and use standard `logging` as usual, calling `.info`, `.error`, etc methods. You can call these functions on the `logger` module itself, or if you're feeling fancy create per-subsystem `Logger` objects so log entries are tagged for filtering convenience via `$OK_LOGGING_LEVEL` (see below).
