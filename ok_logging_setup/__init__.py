"""
Simple opinionated defaults for Python logging, with minimalist formatting,
anti-logspam measures and other minor tweaks.

Activated with ok_logging_setup.install().
"""

from ok_logging_setup._exit import exit
from ok_logging_setup._install import install, install_asyncio_handler
from ok_logging_setup._formatter import skip_traceback_for
