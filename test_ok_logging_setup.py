"""
Test for ok_logging_setup.py, via try_ok_logging_setup.py as a subprocess.
"""

import os
import pathlib
import re
import subprocess
import textwrap


def run_try(*args, **kw):
    PIPE = subprocess.PIPE
    kw = { "stdout": PIPE, "stderr": PIPE, "text": True, "check": 1, **kw }
    args = [pathlib.Path(__file__).parent / "try_ok_logging_setup.py", *args]
    return subprocess.run(args, **kw)


def test_defaults():
    # Note, [Task Name] isn't supported in python 3.9
    assert run_try().stderr == textwrap.dedent("""\
        This is an info message

            ⚠️ This is a warning message with whitespace    

        😎 This is an error message with custom emoji
        💥 This is a critical message
        foo: This is an info message for 'foo'
        🔥 foo: This is an error message for 'foo'
        bar.bat: This is an info message for 'bar.bat'
        🔥 bar.bat: This is an error message for 'bar.bat'
        This is an info message in a task
        🔥 This is an error message in a task
        <Thread Name> This is an info message in a thread
        🔥 <Thread Name> This is an error message in a thread
        This is an info message in an atexit hook
    """)


def test_install_in_thread():
    assert run_try("--install-in-thread").stderr == textwrap.dedent("""\
        <Install Thread> This is an info message

            ⚠️ <Install Thread> This is a warning message with whitespace    

        🔥 <Install Thread> 😎 This is an error message with custom emoji
        💥 <Install Thread> This is a critical message
        foo: <Install Thread> This is an info message for 'foo'
        🔥 foo: <Install Thread> This is an error message for 'foo'
        bar.bat: <Install Thread> This is an info message for 'bar.bat'
        🔥 bar.bat: <Install Thread> This is an error message for 'bar.bat'
        <Install Thread> This is an info message in a task
        🔥 <Install Thread> This is an error message in a task
        <Thread Name> This is an info message in a thread
        🔥 <Thread Name> This is an error message in a thread
        This is an info message in an atexit hook
    """)


def test_keyboard_interrupt():
    stderr = run_try("--keyboard-interrupt", check=0).stderr
    assert stderr == textwrap.dedent("""\

        ❌ KeyboardInterrupt (^C)! ❌
        This is an info message in an atexit hook
    """)


def test_logging_exit():
    stderr = run_try("--ok-logging-exit", check=0).stderr
    assert stderr == textwrap.dedent("""\
        💥 This is a program exit message
        This is an info message in an atexit hook
    """)


def test_uncaught_exception():
    stderr = run_try("--uncaught-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent("""\
        💥 Uncaught exception
        Traceback (most recent call last):
          File XXX, in <module>
            main(args)
          File XXX, in main
            raise Exception("This is an uncaught exception")
        Exception: This is an uncaught exception
        This is an info message in an atexit hook
    """)


def test_uncaught_skip_traceback():
    stderr = run_try("--uncaught-skip-traceback", check=0).stderr
    assert stderr == textwrap.dedent("""\
        💥 Uncaught exception
        SkipTracebackException: This is an uncaught exception with traceback skipped
        This is an info message in an atexit hook
    """)


def test_uncaught_thread_exception():
    stderr = run_try("--uncaught-thread-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent("""\
        💥 <Thread Name> Uncaught exception in thread
        Traceback (most recent call last):
          File XXX, in _bootstrap_inner
            self.run()
          File XXX, in run
            self._target(*self._args, **self._kwargs)
          File XXX, in thread_exception
            raise Exception("This is an uncaught thread exception")
        Exception: This is an uncaught thread exception
    """)


def test_unraisable_exception():
    stderr = run_try("--unraisable-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent("""\
        💥 Uncatchable exception
        Traceback (most recent call last):
          File XXX, in __del__
            raise Exception("This is an 'unraisable' exception")
        Exception: This is an 'unraisable' exception
    """)


def test_env_output():
    env = { **os.environ, "OK_LOGGING_OUTPUT": "stdout" }
    result = run_try(env=env)
    assert result.stderr == ""
    assert result.stdout.startswith("This is an info message")


def test_env_levels():
    env = { **os.environ, "OK_LOGGING_LEVEL": "critical,foo=warn,bar.bat=info" }
    assert run_try(env=env).stderr == textwrap.dedent("""\
        💥 This is a critical message
        🔥 foo: This is an error message for 'foo'
        bar.bat: This is an info message for 'bar.bat'
        🔥 bar.bat: This is an error message for 'bar.bat'
    """)


def test_env_time_format():
    av = ["--fake-time=1/1/2020 12:00Z"]
    env = {
        **os.environ,
        "OK_LOGGING_LEVEL": "critical",  # less output
        "OK_LOGGING_TIME_FORMAT": "%H:%M",
        "OK_LOGGING_TIMEZONE": "America/New_York",
    }
    assert run_try(*av, env=env).stderr == textwrap.dedent("""\
        07:00 💥 This is a critical message
    """)


def test_repeat_limit():
    av = ["--fake-time=1/1/2020", "--spam=25", "--spam-sleep=5"]
    env = { **os.environ, "OK_LOGGING_TIME_FORMAT": "%Y-%m-%d %H:%M:%S" }
    assert run_try(*av, env=env).stderr == textwrap.dedent("""\
        2020-01-01 00:00:00 Spam message 1
        2020-01-01 00:00:05 Spam message 2
        2020-01-01 00:00:10 Spam message 3
        2020-01-01 00:00:15 Spam message 4
        2020-01-01 00:00:20 Spam message 5
        2020-01-01 00:00:25 Spam message 6
        2020-01-01 00:00:30 Spam message 7
        2020-01-01 00:00:35 Spam message 8
        2020-01-01 00:00:40 Spam message 9
        2020-01-01 00:00:45 Spam message 10
        2020-01-01 00:00:50 Spam message 11 [suppressing until 00:01]
        2020-01-01 00:01:00 Spam message 13
        2020-01-01 00:01:05 Spam message 14
        2020-01-01 00:01:10 Spam message 15
        2020-01-01 00:01:15 Spam message 16
        2020-01-01 00:01:20 Spam message 17
        2020-01-01 00:01:25 Spam message 18
        2020-01-01 00:01:30 Spam message 19
        2020-01-01 00:01:35 Spam message 20
        2020-01-01 00:01:40 Spam message 21
        2020-01-01 00:01:45 Spam message 22
        2020-01-01 00:01:50 Spam message 23 [suppressing until 00:02]
        2020-01-01 00:02:00 Spam message 25
        2020-01-01 00:02:05 This is an info message in an atexit hook
    """)
