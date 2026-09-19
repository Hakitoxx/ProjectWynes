"""Safe execution of external processes.

Rules enforced here for every external tool wrapped by Wynes:

- argument lists only, never a shell string (no ``shell=True``)
- mandatory timeout
- console windows are suppressed on Windows
- failures are reported, never silently ignored
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence

from wynes.core.tool_base import ToolResult, ToolStatus

DEFAULT_TIMEOUT = 15

# Hide the console window that external CLI tools would otherwise open
# when Wynes itself runs without a console (pythonw.exe / packaged build).
_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run_process(args: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> ProcessResult:
    """Run ``args`` without a shell and capture its output.

    Never raises for ordinary process failures; timeouts and spawn errors
    surface as exceptions which :func:`guard_exceptions` converts into a
    ``ToolResult``.
    """
    completed = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=_CREATION_FLAGS,
    )
    return ProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def guard_exceptions(fn, **kwargs) -> ToolResult:
    """Run ``fn(**kwargs)`` and convert expected failures into ToolResult.

    This is the single place where worker-thread exceptions become
    user-readable tool failures instead of crashing the application.
    """
    try:
        return fn(**kwargs)
    except subprocess.TimeoutExpired:
        return ToolResult(
            status=ToolStatus.TIMEOUT,
            summary="Operation timed out",
            error="The operation did not finish within the allowed time.",
        )
    except PermissionError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary="Permission denied",
            error=str(exc),
        )
    except FileNotFoundError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary="Required executable not found",
            error=str(exc),
        )
    except OSError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary="Operating system error",
            error=str(exc),
        )
    except Exception as exc:  # last line of defence: report, never crash
        return ToolResult(
            status=ToolStatus.ERROR,
            summary="Unexpected error",
            error=f"{type(exc).__name__}: {exc}",
        )
