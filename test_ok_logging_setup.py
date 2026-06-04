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
    kw = {"stdout": PIPE, "stderr": PIPE, "text": True, "check": 1, **kw}
    args = [pathlib.Path(__file__).parent / "try_ok_logging_setup.py", *args]
    return subprocess.run(args, **kw)


def test_defaults():
    # Note, [Task Name] isn't supported in python 3.9
    assert run_try().stderr == textwrap.dedent(
        """\
        This is an info message

            ⚠️ This is a warning message with whitespace    

        😎 This is an error message with custom emoji
        💥 This is a critical message
        foo: This is an info message for 'foo'
        🔥 foo: This is an error message for 'foo'
        bar.bat: This is an info message for 'bar.bat'
        🔥 bar.bat: This is an error message for 'bar.bat'
        This is an info message in an async task
        🔥 This is an error message in an async task
        <Thread Name> This is an info message in a thread
        🔥 <Thread Name> This is an error message in a thread
        This is an info message in an atexit hook
    """
    )


def test_install_in_thread():
    assert run_try("--install-in-thread").stderr == textwrap.dedent(
        """\
        <Install Thread> This is an info message

            ⚠️ <Install Thread> This is a warning message with whitespace    

        🔥 <Install Thread> 😎 This is an error message with custom emoji
        💥 <Install Thread> This is a critical message
        foo: <Install Thread> This is an info message for 'foo'
        🔥 foo: <Install Thread> This is an error message for 'foo'
        bar.bat: <Install Thread> This is an info message for 'bar.bat'
        🔥 bar.bat: <Install Thread> This is an error message for 'bar.bat'
        <Install Thread> This is an info message in an async task
        🔥 <Install Thread> This is an error message in an async task
        <Thread Name> This is an info message in a thread
        🔥 <Thread Name> This is an error message in a thread
        This is an info message in an atexit hook
    """
    )


def test_keyboard_interrupt():
    stderr = run_try("--keyboard-interrupt", check=0).stderr
    assert stderr == textwrap.dedent(
        """\

        ❌ KeyboardInterrupt (^C)! ❌
        This is an info message in an atexit hook
    """
    )


def test_logging_exit():
    stderr = run_try("--ok-logging-exit", check=0).stderr
    assert stderr == textwrap.dedent(
        """\
        💥 This is a program exit message
        This is an info message in an atexit hook
    """
    )


def test_uncaught_exception():
    stderr = run_try("--uncaught-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent(
        """\
        💥 Uncaught exception
        Traceback (most recent call last):
          File XXX, in <module>
            main(args)
          File XXX, in main
            raise Exception("This is an uncaught exception")
        Exception: This is an uncaught exception
        This is an info message in an atexit hook
    """
    )


def test_uncaught_skip_traceback():
    stderr = run_try("--uncaught-skip-traceback", check=0).stderr
    assert stderr == textwrap.dedent(
        """\
        💥 Uncaught exception
        SkipTracebackException: This is an uncaught exception with traceback skipped
        This is an info message in an atexit hook
    """
    )


def test_uncaught_thread_exception():
    stderr = run_try("--uncaught-thread-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent(
        """\
        💥 <Thread Name> Uncaught exception in thread
        Traceback (most recent call last):
          File XXX, in _bootstrap_inner
            self.run()
          File XXX, in run
            self._target(*self._args, **self._kwargs)
          File XXX, in thread_exception
            raise Exception("This is an uncaught thread exception")
        Exception: This is an uncaught thread exception
    """
    )


def test_uncaught_asyncio_exception():
    stderr = run_try("--uncaught-asyncio-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent(
        """\
        💥 Uncaught exception in asyncio event loop
        Traceback (most recent call last):
          File XXX, in _run
            self._context.run(self._callback, *self._args)
          File XXX, in asyncio_loop_exception
            raise Exception("This is an uncaught asyncio event loop exception")
        Exception: This is an uncaught asyncio event loop exception
    """
    )


def test_unraisable_exception():
    stderr = run_try("--unraisable-exception", check=0).stderr
    assert re.sub(r'".*", line \d+', "XXX", stderr) == textwrap.dedent(
        """\
        💥 Uncatchable exception
        Traceback (most recent call last):
          File XXX, in __del__
            raise Exception("This is an 'unraisable' exception")
        Exception: This is an 'unraisable' exception
    """
    )


def test_env_levels():
    env = {**os.environ, "OK_LOGGING_LEVEL": "critical,foo=warn,bar.bat=info"}
    assert run_try(env=env).stderr == textwrap.dedent(
        """\
        💥 This is a critical message
        🔥 foo: This is an error message for 'foo'
        bar.bat: This is an info message for 'bar.bat'
        🔥 bar.bat: This is an error message for 'bar.bat'
    """
    )


def test_env_prefix():
    env = {**os.environ, "OK_LOGGING_PREFIX": "[MyApp] "}
    assert run_try(env=env).stderr == textwrap.dedent(
        """\
        [MyApp] This is an info message

            [MyApp] ⚠️ This is a warning message with whitespace    

        [MyApp] 😎 This is an error message with custom emoji
        [MyApp] 💥 This is a critical message
        [MyApp] foo: This is an info message for 'foo'
        [MyApp] 🔥 foo: This is an error message for 'foo'
        [MyApp] bar.bat: This is an info message for 'bar.bat'
        [MyApp] 🔥 bar.bat: This is an error message for 'bar.bat'
        [MyApp] This is an info message in an async task
        [MyApp] 🔥 This is an error message in an async task
        [MyApp] <Thread Name> This is an info message in a thread
        [MyApp] 🔥 <Thread Name> This is an error message in a thread
        [MyApp] This is an info message in an atexit hook
        """
    )


def test_env_output():
    env = {**os.environ, "OK_LOGGING_OUTPUT": "stdout"}
    result = run_try(env=env)
    assert result.stderr == ""
    assert result.stdout.startswith("This is an info message")


def test_env_terminator():
    env = {**os.environ, "OK_LOGGING_TERMINATOR": " [EOL]\n"}
    assert run_try(env=env).stderr == textwrap.dedent(
        """\
        This is an info message [EOL]
         [EOL]
            ⚠️ This is a warning message with whitespace     [EOL]
         [EOL]
        😎 This is an error message with custom emoji [EOL]
        💥 This is a critical message [EOL]
        foo: This is an info message for 'foo' [EOL]
        🔥 foo: This is an error message for 'foo' [EOL]
        bar.bat: This is an info message for 'bar.bat' [EOL]
        🔥 bar.bat: This is an error message for 'bar.bat' [EOL]
        This is an info message in an async task [EOL]
        🔥 This is an error message in an async task [EOL]
        <Thread Name> This is an info message in a thread [EOL]
        🔥 <Thread Name> This is an error message in a thread [EOL]
        This is an info message in an atexit hook [EOL]
        """
    )


def test_env_time_format():
    av = ["--fake-time=1/1/2020 12:00Z"]
    env = {
        **os.environ,
        "OK_LOGGING_LEVEL": "critical",  # less output
        "OK_LOGGING_TIME_FORMAT": "%H:%M",
        "OK_LOGGING_TIMEZONE": "America/New_York",
    }
    assert run_try(*av, env=env).stderr == textwrap.dedent(
        """\
        07:00 💥 This is a critical message
    """
    )


def test_repeat_limit():
    av = ["--fake-time=1/1/2020", "--spam=35", "--spam-sleep=0.2"]
    env = {**os.environ, "OK_LOGGING_TIME_FORMAT": "%H:%M:%S.%f"}
    assert run_try(*av, env=env).stderr == textwrap.dedent(
        """\
        00:00:00.000000 Spam message 1
        00:00:00.200000 Spam message 2
        00:00:00.400000 Spam message 3
        00:00:00.600000 Spam message 4
        00:00:00.800000 Spam message 5
        00:00:01.000000 Spam message 6
        00:00:01.200000 Spam message 7
        00:00:01.400000 Spam message 8
        00:00:01.600000 Spam message 9
        00:00:01.800000 Spam message 10
        00:00:02.000000 Spam message 11
        00:00:02.200000 Spam message 12
        00:00:02.400000 Spam message 13
        00:00:02.600000 Spam message 14
        00:00:02.800000 Spam message 15
        00:00:03.000000 Spam message 16
        00:00:03.200000 Spam message 17
        00:00:03.400000 Spam message 18
        00:00:03.600000 Spam message 19
        00:00:03.800000 Spam message 20
        00:00:04.000000 Spam message 21
        00:00:04.200000 Spam message 22
        00:00:04.400000 Spam message 23
        00:00:04.600000 Spam message 24 ⏱️ [rate limiting]
        00:00:05.000000 Spam message 26 ⏱️ [rate limiting]
        00:00:06.000000 Spam message 31 ⏱️ [rate limiting]
        00:00:07.000000 This is an info message in an atexit hook
        """
    )

    # Messages with {"repeat_ok": True} bypass spam protection
    av_repeat_ok = [*av, "--spam-repeat-ok"]
    assert run_try(*av_repeat_ok, env=env).stderr == textwrap.dedent(
        """\
        00:00:00.000000 Spam message 1
        00:00:00.200000 Spam message 2
        00:00:00.400000 Spam message 3
        00:00:00.600000 Spam message 4
        00:00:00.800000 Spam message 5
        00:00:01.000000 Spam message 6
        00:00:01.200000 Spam message 7
        00:00:01.400000 Spam message 8
        00:00:01.600000 Spam message 9
        00:00:01.800000 Spam message 10
        00:00:02.000000 Spam message 11
        00:00:02.200000 Spam message 12
        00:00:02.400000 Spam message 13
        00:00:02.600000 Spam message 14
        00:00:02.800000 Spam message 15
        00:00:03.000000 Spam message 16
        00:00:03.200000 Spam message 17
        00:00:03.400000 Spam message 18
        00:00:03.600000 Spam message 19
        00:00:03.800000 Spam message 20
        00:00:04.000000 Spam message 21
        00:00:04.200000 Spam message 22
        00:00:04.400000 Spam message 23
        00:00:04.600000 Spam message 24
        00:00:04.800000 Spam message 25
        00:00:05.000000 Spam message 26
        00:00:05.200000 Spam message 27
        00:00:05.400000 Spam message 28
        00:00:05.600000 Spam message 29
        00:00:05.800000 Spam message 30
        00:00:06.000000 Spam message 31
        00:00:06.200000 Spam message 32
        00:00:06.400000 Spam message 33
        00:00:06.600000 Spam message 34
        00:00:06.800000 Spam message 35
        00:00:07.000000 This is an info message in an atexit hook
        """
    )

    # DEBUG messages bypass spam protection
    av_debug = [*av, "--spam-level=debug"]
    env_debug = {"OK_LOGGING_LEVEL": "debug", **env}
    assert run_try(*av_debug, env=env_debug).stderr == textwrap.dedent(
        """\
        00:00:00.000000 🕸  Spam message 1
        00:00:00.200000 🕸  Spam message 2
        00:00:00.400000 🕸  Spam message 3
        00:00:00.600000 🕸  Spam message 4
        00:00:00.800000 🕸  Spam message 5
        00:00:01.000000 🕸  Spam message 6
        00:00:01.200000 🕸  Spam message 7
        00:00:01.400000 🕸  Spam message 8
        00:00:01.600000 🕸  Spam message 9
        00:00:01.800000 🕸  Spam message 10
        00:00:02.000000 🕸  Spam message 11
        00:00:02.200000 🕸  Spam message 12
        00:00:02.400000 🕸  Spam message 13
        00:00:02.600000 🕸  Spam message 14
        00:00:02.800000 🕸  Spam message 15
        00:00:03.000000 🕸  Spam message 16
        00:00:03.200000 🕸  Spam message 17
        00:00:03.400000 🕸  Spam message 18
        00:00:03.600000 🕸  Spam message 19
        00:00:03.800000 🕸  Spam message 20
        00:00:04.000000 🕸  Spam message 21
        00:00:04.200000 🕸  Spam message 22
        00:00:04.400000 🕸  Spam message 23
        00:00:04.600000 🕸  Spam message 24
        00:00:04.800000 🕸  Spam message 25
        00:00:05.000000 🕸  Spam message 26
        00:00:05.200000 🕸  Spam message 27
        00:00:05.400000 🕸  Spam message 28
        00:00:05.600000 🕸  Spam message 29
        00:00:05.800000 🕸  Spam message 30
        00:00:06.000000 🕸  Spam message 31
        00:00:06.200000 🕸  Spam message 32
        00:00:06.400000 🕸  Spam message 33
        00:00:06.600000 🕸  Spam message 34
        00:00:06.800000 🕸  Spam message 35
        00:00:07.000000 This is an info message in an atexit hook
        """
    )
