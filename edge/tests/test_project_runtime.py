"""TASK-NEW-EDGE-RUNTIME-01: choose Python before dependencies or hardware."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_runtime


def runtime_fixture(tmp_path, monkeypatch):
    root = tmp_path / "Project with spaces"
    script = root / "edge" / "launcher.py"
    script.parent.mkdir(parents=True)
    script.touch()
    environment = root / ".venv"
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(sys, "prefix", str(root / "other-python"))
    return script, environment, executable


def test_global_python_restarts_in_project_environment_and_preserves_arguments(tmp_path, monkeypatch):
    script, environment, executable = runtime_fixture(tmp_path, monkeypatch)
    run = Mock(return_value=7)
    monkeypatch.setattr(project_runtime.subprocess, "call", run)
    monkeypatch.setenv("PYTHONHOME", "wrong-home")
    monkeypatch.setenv("PYTHONPATH", "conflicting-serial")
    assert project_runtime.restart_in_project_environment(script, ["--check-runtime", "argument with spaces"]) == 7
    assert run.call_args.args[0] == [str(executable), str(script), "--check-runtime", "argument with spaces"]
    assert "PYTHONHOME" not in run.call_args.kwargs["env"]
    assert "PYTHONPATH" not in run.call_args.kwargs["env"]
    assert os.environ["PYTHONPATH"] == "conflicting-serial"


def test_selected_environment_does_not_restart_recursively(tmp_path, monkeypatch):
    script, environment, _ = runtime_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.delenv("PYTHONHOME", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    run = Mock()
    monkeypatch.setattr(project_runtime.subprocess, "call", run)
    assert project_runtime.restart_in_project_environment(script) is None
    run.assert_not_called()


def test_selected_environment_restarts_once_if_python_path_is_polluted(tmp_path, monkeypatch):
    script, environment, _ = runtime_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.setenv("PYTHONPATH", "conflicting-serial")
    run = Mock(return_value=0)
    monkeypatch.setattr(project_runtime.subprocess, "call", run)
    assert project_runtime.restart_in_project_environment(script, []) == 0
    assert "PYTHONPATH" not in run.call_args.kwargs["env"]


def test_no_project_environment_preserves_existing_install(tmp_path, monkeypatch):
    run = Mock()
    monkeypatch.setattr(project_runtime.subprocess, "call", run)
    assert project_runtime.restart_in_project_environment(tmp_path / "edge" / "launcher.py") is None
    run.assert_not_called()


@pytest.mark.parametrize("available", [True, False])
def test_runtime_check_imports_serial_without_opening_a_port(monkeypatch, capsys, available):
    constructor = Mock()
    serial = SimpleNamespace(__file__="project/serial/__init__.py", __version__="3.5")
    if available:
        serial.Serial = constructor
    monkeypatch.setitem(sys.modules, "serial", serial)
    assert project_runtime.check_runtime() == (0 if available else 1)
    constructor.assert_not_called()
    assert "Python:" in capsys.readouterr().out
