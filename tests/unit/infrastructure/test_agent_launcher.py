"""Background Agent launcher tests — ``subprocess.Popen`` is recorded, never run."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import pytest

from insightflow.infrastructure.process import agent_launcher
from insightflow.infrastructure.process.agent_launcher import (
    AGENT_MODULE,
    launch_background_agent,
    windowless_interpreter,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Agent launching is Windows-only."
)


class _RecordingPopen:
    calls: ClassVar[list[tuple[list[str], dict[str, Any]]]] = []

    def __init__(self, args: list[str], **kwargs: Any) -> None:
        _RecordingPopen.calls.append((args, kwargs))


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingPopen]:
    _RecordingPopen.calls = []
    monkeypatch.setattr(agent_launcher.subprocess, "Popen", _RecordingPopen)
    return _RecordingPopen


def test_launch_starts_detached_agent_module(
    recorded: type[_RecordingPopen], tmp_path: Path
) -> None:
    launch_background_agent(log_dir=tmp_path / "logs")

    assert len(recorded.calls) == 1
    args, kwargs = recorded.calls[0]
    assert args[1:] == ["-m", AGENT_MODULE]
    assert kwargs["stdin"] is subprocess.DEVNULL
    detached = 0x00000008
    assert kwargs["creationflags"] & detached
    assert (tmp_path / "logs" / "agent-output.log").exists()


def test_windowless_interpreter_prefers_pythonw(tmp_path: Path) -> None:
    python = tmp_path / "python.exe"
    python.write_text("")
    (tmp_path / "pythonw.exe").write_text("")

    assert windowless_interpreter(str(python)) == str(tmp_path / "pythonw.exe")


def test_windowless_interpreter_falls_back_without_pythonw(tmp_path: Path) -> None:
    python = tmp_path / "python.exe"
    python.write_text("")

    assert windowless_interpreter(str(python)) == str(python)
