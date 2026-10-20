"""Select the project interpreter before importing any application dependencies."""
import os
from pathlib import Path
import subprocess
import sys


def restart_in_project_environment(script, arguments=None):
    script = Path(script).resolve()
    environment = script.parent.parent / ".venv"
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        return None
    already_selected = Path(sys.prefix).resolve() == environment.resolve()
    polluted_path = any(os.environ.get(name) for name in ("PYTHONHOME", "PYTHONPATH"))
    if already_selected and not polluted_path:
        return None
    child_environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH"):
        child_environment.pop(name, None)
    return subprocess.call([str(executable), str(script), *(sys.argv[1:] if arguments is None else arguments)],
                           env=child_environment)


def check_runtime():
    """Read-only import check; never enumerate or open a serial port."""
    import serial
    print(f"Python: {sys.executable}")
    print(f"Serial module: {serial.__file__}")
    if not callable(getattr(serial, "Serial", None)):
        print("PySerial unavailable. Install edge/requirements.txt in the project .venv.")
        return 1
    print(f"PySerial {getattr(serial, '__version__', 'unknown')}: ready")
    return 0
