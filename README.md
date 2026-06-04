<!-- markdownlint-disable MD013 -->

# ok-logging-setup for Python

Basic, opinionated [Python logging](https://docs.python.org/3/library/logging.html) setup with env-var config, logspam limiting and minimalist formatting.

You probably won't want to use this. You should consider these libraries instead:

- [structlog](https://www.structlog.org/) - fancy logging system with interconnects to Python logging
- [Rich](https://github.com/Textualize/rich#readme) - pretty text formatter, includes a logging prettifier
- [Pretty Pie Log](https://github.com/chanpreet3000/pretty-pie-log) - logging prettifier
- [logging518](https://github.com/mharrisb1/logging518) - configure logging in pyproject.toml (or another TOML file)
- [Easy Logging](https://github.com/Kiennguyen08/easy-logging-setup) - logging setup with YAML configuration
- [simple-logging-setup](https://github.com/fscherf/simple-logging-setup) - a colorful take on logging defaults
- [setup logging for me](https://github.com/jmansilla/setup_logging_for_me) - even more minimal and idiosyncratic than this package!

## Opinion-ifesto

Python's `logging` module is usable enough but (over)complicated with a tree of loggers with attached handlers, formatters, and filters, plus similarly (over)complicated [external configuration](https://docs.python.org/3/library/logging.config.html) using ini-files and/or a custom socket protocol (!) to customize that whole mess.

Modern [12-factor-ish apps](https://12factor.net/) don't want most of this. Logging should just go to stderr in some reasonable format; the app runner (Docker, systemd, etc) takes it from there. I just need an environment variable to dial verbosity up and down for the app or subsystems I'm debugging. That's what this library offers.

Finally, most logging formatters spend too much real estate on log levels, source locations, full timestamps, and other metadata. This library adds a minimalist formatter that skips most of that (see below). You can always search the code to find a message's origin! (Stack traces are still printed for exceptions.)

## Usage

Add this package as a dependency:

- `pip install ok-logging-setup`
- OR copy `ok_logging_setup/` (it has no dependencies)

Import the module and call `ok_logging_setup.install()` near program start:

```python
import ok_logging_setup
...
def main():
    ok_logging_setup.install()
    ... run your app ...
```

The call to `ok_logging_setup.install()` does the following:

- makes a root stderr logger via [`logging.basicConfig`](https://docs.python.org/3/library/logging.html#logging.basicConfig)
- interprets `$OK_LOGGING_*` environment variables (described below)
- adds a formatter with minimal, legible output (described below)
- adds a filter with simple logspam-protection (described below)
- adds an uncaught exception handler that uses this logger
- adds a thread exception handler that uses this logger *and exits*
- adds an "unraisable" exception handler that uses this logger *and exits*
- changes `sys.stdout` to line buffered, so `print` and logs interleave correctly
- resets control-C handling (`SIGINT`) to insta-kill (`SIG_DFL`), not Python's `InterruptException` nonsense

Extra goodies:

- pass a string-string dict to `ok_logging_setup.install({ ... })` to set defaults (see below)
- call `ok_logging_setup.exit(msg, ...)` to log a `.critical(msg, ...)` and immediately `sys.exit(1)`
- call `ok_logging_setup.skip_traceback_for(SomeClass)` to not print stacks for that exception
- call `ok_logging_setup.install_asyncio_handler()` in an event loop to log uncaught exceptions *and exit*

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

### `$OK_LOGGING_PREFIX` (default empty)

This string is printed before each log message.

### `$OK_LOGGING_REPEAT_BURST` (default 20)

Maximum times a "similar" message can be repeated before rate limiting (see below).

### `$OK_LOGGING_REPEAT_DELAY` (default 1.0)

Minimum seconds between "similar" messages being rate limited (see below).

### `$OK_LOGGING_TERMINATOR` (default `\n`)

This string is printed after each log message to end the line.

### `$OK_LOGGING_TIME_FORMAT` and `$OK_LOGGING_TIMEZONE`

- to timestamp log messages, set `$OK_LOGGING_TIME_FORMAT` to a [`strftime` format](https://docs.python.org/3/library/datetime.html#format-codes)
- if set, `$OK_LOGGING_TIMEZONE` ([from this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) is used for timestamps

## Spam protection rate limiting

If a message gets emitted in a tight loop somehow, it can slow code down, fill up disks, bury other logs, and generally make a bad day. To mitigate this, `ok_logging_setup.install` adds a filter that checks for repeated "similar" messages (same text not counting digits). When that happens, the offending message is rate limited with a "cooldown".

DEBUG messages are exempt as they are assumed to be noisy by design. Messages with `"repeat_ok"` in `extra` are also exempt.

`$OK_LOGGING_REPEAT_BURST` and `$OK_LOGGING_REPEAT_DELAY` control the rate limiting. For example, with the defaults of `20` and `1.0`, after 20 similar messages in excess of 1/sec, further messages of that type are culled to no more than 1/sec with a `⏱️ [rate limiting]` marker.

```text
% OK_LOGGING_TIME_FORMAT=%H:%M:%S.%f ./try_ok_logging_setup.py --spam=50 --spam-sleep=0.2 --fake-time 11:40
11:40:00.000000 Spam message 1
11:40:00.200000 Spam message 2
11:40:00.400000 Spam message 3
11:40:00.600000 Spam message 4
11:40:00.800000 Spam message 5
11:40:01.000000 Spam message 6
11:40:01.200000 Spam message 7
11:40:01.400000 Spam message 8
11:40:01.600000 Spam message 9
11:40:01.800000 Spam message 10
11:40:02.000000 Spam message 11
11:40:02.200000 Spam message 12
11:40:02.400000 Spam message 13
11:40:02.600000 Spam message 14
11:40:02.800000 Spam message 15
11:40:03.000000 Spam message 16
11:40:03.200000 Spam message 17
11:40:03.400000 Spam message 18
11:40:03.600000 Spam message 19
11:40:03.800000 Spam message 20
11:40:04.000000 Spam message 21
11:40:04.200000 Spam message 22
11:40:04.400000 Spam message 23
11:40:04.600000 Spam message 24 ⏱️ [rate limiting]
11:40:05.000000 Spam message 26 ⏱️ [rate limiting]
11:40:06.000000 Spam message 31 ⏱️ [rate limiting]
11:40:07.000000 Spam message 36 ⏱️ [rate limiting]
11:40:08.000000 Spam message 41 ⏱️ [rate limiting]
11:40:09.000000 Spam message 46 ⏱️ [rate limiting]
...
```

In this case, filtering started at message 24 because 4 seconds had elapsed since the start of the burst, so there were 20 messages exceeding the 1/sec rate. Once the storm subsides, the burst quota can rebuild up to the maximum 20.

This filtering is per message; a different message would have its own burst and cooldown. This is determined by stripping digits from the message text, so `Spam message 1` and `Spam message 2` are considered similar, but `Spam message 1` and `Another message 1` are not.

## Log format

By default, log messages include a severity icon (emoji) and the message:

```text
🕸 This is a debug message
This is an INFO message
⚠️ This is a WARNING message    
🔥 This is an ERROR message
💥 This is a CRITICAL message
```

(If the message already starts with an emoji, no emoji prefix is added; your emoji is assumed to convey appropriate importance.)

If the message is logged with a named `Logger` object, the name is added as a prefix:

```text
🔥 foo: This is an error message reported with a Logger named "foo"
```

If the message is logged from a named thread or a named asyncio task, the name is included

```text
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

```text
💥 Uncaught exception
Traceback (most recent call last):
  File "/home/egnor/source/ok-py-logging-setup/try_ok_logging_setup.py", line 109, in <module>
    main()
  File "/home/egnor/source/ok-py-logging-setup/try_ok_logging_setup.py", line 55, in main
    raise Exception("This is an uncaught exception")
Exception: This is an uncaught exception
```
