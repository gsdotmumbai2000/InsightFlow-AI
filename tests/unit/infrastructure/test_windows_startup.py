"""WindowsScheduledTaskStartup tests (Phase 13) — mocked subprocess, no real
``schtasks.exe`` calls."""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

from insightflow.infrastructure.process.windows_startup import (
    WindowsScheduledTaskStartup,
)


def _completed(
    returncode: int, stderr: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stderr=stderr)


def test_is_registered_true_when_query_succeeds() -> None:
    startup = WindowsScheduledTaskStartup(task_name="Test Task")
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        assert startup.is_registered() is True
    args = mock_run.call_args[0][0]
    assert args[:3] == ["schtasks", "/Query", "/TN"]
    assert "Test Task" in args


def test_is_registered_false_when_query_fails() -> None:
    startup = WindowsScheduledTaskStartup(task_name="Test Task")
    with patch("subprocess.run", return_value=_completed(1)):
        assert startup.is_registered() is False


def test_register_invokes_schtasks_create_with_no_admin_no_password_flags() -> None:
    startup = WindowsScheduledTaskStartup(
        task_name="Test Task",
        agent_command='"C:\\py.exe" -m insightflow.bootstrap.agent',
    )
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        startup.register()
    args: list[Any] = mock_run.call_args[0][0]
    assert args[0] == "schtasks"
    assert "/Create" in args
    assert "ONLOGON" in args  # runs at logon, in the interactive session
    assert "/RU" not in args  # no explicit run-as-user
    assert "/RP" not in args  # no stored password
    assert "LIMITED" in args  # least privilege, no admin
    tr_index = args.index("/TR")
    assert args[tr_index + 1] == '"C:\\py.exe" -m insightflow.bootstrap.agent'


def test_register_raises_on_schtasks_failure() -> None:
    startup = WindowsScheduledTaskStartup(task_name="Test Task")
    with patch("subprocess.run", return_value=_completed(1, b"access denied")):
        try:
            startup.register()
        except RuntimeError as exc:
            assert "access denied" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")


def test_unregister_invokes_schtasks_delete() -> None:
    startup = WindowsScheduledTaskStartup(task_name="Test Task")
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        startup.unregister()
    args = mock_run.call_args[0][0]
    assert args == ["schtasks", "/Delete", "/TN", "Test Task", "/F"]


def test_unregister_is_idempotent_when_task_already_absent() -> None:
    startup = WindowsScheduledTaskStartup(task_name="Test Task")
    with patch(
        "subprocess.run",
        return_value=_completed(
            1, b"ERROR: The system cannot find the file specified."
        ),
    ):
        startup.unregister()  # must not raise


def test_default_agent_command_uses_current_interpreter() -> None:
    from insightflow.infrastructure.process.windows_startup import (
        default_agent_command,
    )

    command = default_agent_command()
    assert "insightflow.bootstrap.agent" in command
