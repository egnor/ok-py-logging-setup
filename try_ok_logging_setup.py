#!/usr/bin/env python3

import argparse
import logging
import ok_logging_setup
import threading

"""Exercise logging with ok_logging_setup. Used by test_ok_logging_setup.py"""

class SkipTrackbackException(Exception): pass
ok_logging_setup.skip_traceback_for(SkipTrackbackException)

def main():
    parser = argparse.ArgumentParser(description="Test ok_logging_setup")
    parser.add_argument("--default-level", default="INFO")
    parser.add_argument("--default-per-minute", default=10)
    except_args = parser.add_mutually_exclusive_group()
    except_args.add_argument("--uncaught-exception", action="store_true")
    except_args.add_argument("--uncaught-skip-traceback", action="store_true")
    except_args.add_argument("--uncaught-thread-exception", action="store_true")
    except_args.add_argument("--unraisable-exception", action="store_true")

    args = parser.parse_args()

    # Setup logging
    ok_logging_setup.install(
        default_level=args.default_level,
        default_per_minute=args.default_per_minute,
    )

    # Log messages at different levels
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")

    logging.warning("\n    This is a warning message with whitespace    \n")

    foo_logger = logging.getLogger("foo")
    foo_logger.info("This is an info message for 'foo'")
    foo_logger.error("This is an error message for 'foo'")

    barbat_logger = logging.getLogger("bar.bat")
    barbat_logger.info("This is an info message for 'bar.bat'")
    barbat_logger.error("This is an error message for 'bar.bat'")

    if args.uncaught_exception:
        raise Exception("This is an uncaught exception")

    if args.uncaught_skip_traceback:
        raise SkipTrackbackException(
            "This is an uncaught exception with traceback skipped"
        )

    if args.uncaught_thread_exception:
        def do_raise():
            raise Exception("This is an uncaught thread exception")
        thread = threading.Thread(name="Exception Thread", target=do_raise)
        thread.start()
        thread.join()

    if args.unraisable_exception:
        class DestructorRaises:
            def __del__(self):
                raise Exception("This is an 'unraisable' exception")
        obj = DestructorRaises()
        del obj


if __name__ == "__main__":
    main()
