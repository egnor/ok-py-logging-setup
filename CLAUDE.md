# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Project uses `mise` + `uv`. After cloning, `uv sync` (or the mise `postinstall` hook) creates `.venv`.

- Full check: `mise run check` (runs `uv sync`, `black --check .`, `ruff check`, `mypy`, `pytest`)
- Single test: `uv run pytest test_ok_logging_setup.py::test_defaults`
- Format: `uv run black .`
- Type check: `uv run mypy`

## Architecture

`ok_logging_setup` is a zero-dependency, opinionated wrapper around stdlib `logging`. One public entry point — `install()` — wires a single `StreamHandler` (stderr) with a custom `LogFormatter` + `LogFilter`, then reads `$OK_LOGGING_*` env vars to configure it. Never adds multiple handlers; `install()` is idempotent but refuses to run if unrelated handlers already exist.

Module split (all private except `__init__.py` re-exports):

- `_install.py` — `install()`, env-var parsing, and exception hooks. The hooks (`sys.excepthook`, `sys.unraisablehook`, `threading.excepthook`, and the opt-in asyncio handler from `install_asyncio_handler()`) deliberately call `os._exit(1)` on unraisable/thread/asyncio errors — policy choice to fail the whole process rather than let a crashed thread leave a zombie app. This bypasses `atexit`, which is intentional.
- `_formatter.py` — `LogFormatter` prepends severity emoji (skipped if message already starts with an emoji, detected via `unicodedata.category == "So"`), logger name, thread/task name, optional timestamp. Module-level globals `log_prefix`, `log_time_format`, `log_timezone`, `skip_traceback_types` are mutated by `_install._configure()` and `skip_traceback_for()`.
- `_filter.py` — `LogFilter` does per-minute spam suppression, keyed by a "signature" (format string + string args with digits replaced by `#`). DEBUG messages and records with `extra={"repeat_ok": True}` bypass the filter. Module-level `repeat_per_minute` is the knob.
- `_exit.py` — `exit()` helper: critical-log then `SystemExit`.

Tests run `try_ok_logging_setup.py` as a subprocess and assert on exact stderr/stdout text — so changes to formatting output must be reflected in the expected strings in `test_ok_logging_setup.py`. Don't mock logging; tests rely on real subprocess behavior to exercise exception hooks and signal handling.

Configuration precedence: actual `os.environ` overrides the `env_defaults` dict passed to `install()`.
