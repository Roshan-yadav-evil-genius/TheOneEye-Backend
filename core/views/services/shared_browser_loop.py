"""
Shared browser/executor event loop.

Provides a single long-lived event loop running in a daemon thread so that
browser contexts (Playwright) can be reused across API workflow and single-node
execution requests. No cleanup or loop.close() in this module; the loop runs
until process exit.
"""

import asyncio
import threading
from typing import Optional

_shared_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def get_shared_loop() -> asyncio.AbstractEventLoop:
    """Return the shared executor loop, starting the loop thread lazily."""
    global _shared_loop, _loop_thread
    with _loop_lock:
        if _shared_loop is None:
            _shared_loop = asyncio.new_event_loop()

            def _run_loop():
                asyncio.set_event_loop(_shared_loop)
                _shared_loop.run_forever()

            _loop_thread = threading.Thread(target=_run_loop, daemon=True)
            _loop_thread.start()
            # Wait until loop is running
            while not _shared_loop.is_running():
                threading.Event().wait(0.01)
        return _shared_loop
