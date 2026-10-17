"""Start the Background Agent from the Desktop app.

The Desktop never owns the monitoring or AI workers (see ``ProcessRole``),
so without a running Agent nothing is monitored or analyzed. Launching it
here means starting the Desktop is enough; the Windows logon task remains
the way it starts without the Desktop.

No "is it already running?" probe: the Agent's own ``SingleInstanceLock``
makes a second Agent exit immediately, and probing that lock from here
could briefly hold it and make a genuinely starting Agent exit instead.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AGENT_MODULE = "insightflow.bootstrap.agent"
AGENT_OUTPUT_FILENAME = "agent-output.log"

# Windows process-creation flags: no console window, and not part of the
# Desktop's console/process group, so closing the Desktop (or the console
# it was started from) never stops the Agent.
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def windowless_interpreter(executable: str = sys.executable) -> str:
    """``pythonw.exe`` beside ``python.exe`` when present, else ``executable``."""
    path = Path(executable)
    if path.name.lower() == "python.exe":
        pythonw = path.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return executable


def launch_background_agent(*, log_dir: Path) -> None:
    """Start a detached Agent process; returns without waiting for it.

    Its stdout/stderr go to ``log_dir/agent-output.log`` so a windowless
    Agent's startup errors are still visible somewhere.
    """
    if sys.platform != "win32":
        raise RuntimeError("Launching the Background Agent requires Windows.")
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / AGENT_OUTPUT_FILENAME).open("ab") as output:
        subprocess.Popen(
            [windowless_interpreter(), "-m", AGENT_MODULE],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            close_fds=True,
            creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
        )
