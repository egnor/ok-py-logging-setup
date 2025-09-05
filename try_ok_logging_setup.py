#!/usr/bin/env python3

import argparse
import asyncio
import asyncio.events
import atexit
import logging
import ok_logging_setup
import threading
import time
import time_machine

"""Exercise logging with ok_logging_setup. Used by test_ok_logging_setup.py"""

class SkipTracebackException(Exception):
    pass

ok_logging_setup.skip_traceback_for(SkipTracebackException)


def atexit_hook():
    logging.info("This is an info message in an atexit hook")


async def task_function():
    logging.info("This is an info message in a task")
    logging.error("This is an error message in a task")


def thread_function():
    logging.info("This is an info message in a thread")
    logging.error("This is an error message in a thread")


def thread_exception():
    raise Exception("This is an uncaught thread exception")


def main(args):
    # Register atexit to verify
    atexit.register(atexit_hook)

    # If requested, set up different logging first
    if args.logging_conflict:
        logging.basicConfig()

    # Setup logging
    ok_logging_setup.install()

    # Do it again to make sure that's okay
    ok_logging_setup.install({})

    # Fake timestamp if requested
    fake_time = None
    if args.fake_time:
        time_travel = time_machine.travel(args.fake_time, tick=False)
        fake_time = time_travel.start()

    # Optional fatal error modes
    if args.keyboard_interrupt:
        raise KeyboardInterrupt()

    if args.ok_logging_exit:
        ok_logging_setup.exit("This is a program exit message")

    if args.sys_exit:
        raise SystemExit(2)

    if args.uncaught_exception:
        raise Exception("This is an uncaught exception")

    if args.uncaught_skip_traceback:
        raise SkipTracebackException(
            "This is an uncaught exception with traceback skipped"
        )

    if args.uncaught_thread_exception:
        thread = threading.Thread(name="Thread Name", target=thread_exception)
        thread.start()
        thread.join()

    if args.unraisable_exception:
        class DestructorRaises:
            def __del__(self):
                raise Exception("This is an 'unraisable' exception")
        obj = DestructorRaises()
        del obj

    # Log spam test
    if args.spam:
        for i in range(args.spam):
            logging.info(f"Spam message {i + 1}")
            if fake_time:
                fake_time.shift(args.spam_sleep)
            else:
                time.sleep(args.spam_sleep)
        return

    # Log messages at different levels
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("\n    This is a warning message with whitespace    \n")
    logging.error("😎 This is an error message with custom emoji")
    logging.critical("This is a critical message")

    foo_logger = logging.getLogger("foo")
    foo_logger.info("This is an info message for 'foo'")
    foo_logger.error("This is an error message for 'foo'")

    barbat_logger = logging.getLogger("bar.bat")
    barbat_logger.info("This is an info message for 'bar.bat'")
    barbat_logger.error("This is an error message for 'bar.bat'")

    async_loop = asyncio.events.new_event_loop()
    async_task = async_loop.create_task(task_function(), name="Task Name")
    async_loop.run_until_complete(async_task)

    thread = threading.Thread(name="Thread Name", target=thread_function)
    thread.start()
    thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake-time")
    parser.add_argument("--install-in-thread", action="store_true")
    parser.add_argument("--spam", type=int, default=0)
    parser.add_argument("--spam-sleep", type=float, default=0)
    fatal_args = parser.add_mutually_exclusive_group()
    fatal_args.add_argument("--keyboard-interrupt", action="store_true")
    fatal_args.add_argument("--logging-conflict", action="store_true")
    fatal_args.add_argument("--ok-logging-exit", action="store_true")
    fatal_args.add_argument("--sys-exit", action="store_true")
    fatal_args.add_argument("--uncaught-exception", action="store_true")
    fatal_args.add_argument("--uncaught-skip-traceback", action="store_true")
    fatal_args.add_argument("--uncaught-thread-exception", action="store_true")
    fatal_args.add_argument("--unraisable-exception", action="store_true")
    args = parser.parse_args()

    if args.install_in_thread:
        run = threading.Thread(name="Install Thread", target=main, args=(args,))
        run.start()
        run.join()
    else:
        main(args)
