"""Boot synchronization for standalone diagnostics, before identity or actuation."""
import time

def open_diagnostic_port(*args, stop_event=None, **kwargs):
    import serial
    connection = None
    for attempt in range(4):
        try:
            connection = serial.Serial(*args, **kwargs)
            break
        except (serial.SerialException, OSError):
            if attempt == 3:
                raise
            if stop_event is not None and stop_event.wait(.5):
                raise RuntimeError("Test stopped during serial startup")
            time.sleep(.5)
    try:
        if stop_event is None:
            time.sleep(2)
        elif stop_event.wait(2):
            raise RuntimeError("Test stopped during serial startup")
        connection.reset_input_buffer()
        if connection.write(b"\n") != 1:
            raise RuntimeError("Incomplete serial startup delimiter write")
        # Terminate any old partial line and drain its reply before a fresh HELLO.
        # No fault acknowledgement or output command has been sent at this point.
        deadline = time.monotonic() + 1
        quiet_since = time.monotonic()
        while time.monotonic() - quiet_since < .2:
            if stop_event is not None and stop_event.is_set():
                raise RuntimeError("Test stopped during serial startup")
            if time.monotonic() >= deadline:
                raise RuntimeError("Serial startup input did not settle; check firmware and USB connection")
            if connection.read(256):
                quiet_since = time.monotonic()
        return connection
    except BaseException:
        if connection is not None:
            connection.close()
        raise
