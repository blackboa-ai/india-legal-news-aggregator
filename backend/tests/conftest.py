"""
Pytest Fixtures and Global Test Configuration
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Enable asyncio event loop to operate cleanly in sandboxed environments without loopback socketpair
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import BaseProactorEventLoop

        def _dummy_make_self_pipe(self):
            self._ssock = None
            self._csock = None
            self._internal_fds += 1

        def _dummy_close_self_pipe(self):
            pass

        def _dummy_loop_self_reading(self, f=None):
            pass

        def _dummy_write_to_self(self):
            pass

        BaseProactorEventLoop._make_self_pipe = _dummy_make_self_pipe
        BaseProactorEventLoop._close_self_pipe = _dummy_close_self_pipe
        BaseProactorEventLoop._loop_self_reading = _dummy_loop_self_reading
        BaseProactorEventLoop._write_to_self = _dummy_write_to_self

        orig_init = BaseProactorEventLoop.__init__

        def new_init(self, proactor):
            super(BaseProactorEventLoop, self).__init__()
            self._proactor = proactor
            self._selector = proactor
            self._self_reading_future = None
            self._accept_futures = {}
            proactor.set_loop(self)
            self._make_self_pipe()

        BaseProactorEventLoop.__init__ = new_init
    except Exception:
        pass

