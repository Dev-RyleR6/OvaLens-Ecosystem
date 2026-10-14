"""Keep cyclic Tk object cleanup on pytest's main thread between tests."""
import gc
import pytest


@pytest.fixture(autouse=True)
def collect_cycles_on_test_thread():
    # Repeated native windows leave widget/Variable cycles. Automatic collection
    # on a simulated serial worker can stall it while Tk waits for a main loop
    # that the previous test already closed. Collect explicitly between tests.
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        gc.collect()
        if was_enabled:
            gc.enable()
