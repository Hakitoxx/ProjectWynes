"""Safe execution of external processes.

Rules enforced here for every external tool wrapped by Wynes:

- argument lists only, never a shell string (no ``shell=True``)
- mandatory timeout
- console windows are suppressed on Windows
- failures are reported, never silently ignored
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence

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


def decode_console_bytes(data: bytes) -> str:
    """Decode console output robustly.

    Console utilities write in the machine's *OEM* code page (e.g. cp857 on
    a Turkish Windows), not necessarily in UTF-8 or the ANSI code page.
    Trying UTF-8 first, then the OEM code page, keeps structured markers
    intact and never raises.
    """
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    encoding = ""
    if sys.platform.startswith("win"):
        try:
            import ctypes

            encoding = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:
            encoding = ""
    if encoding:
        try:
            return data.decode(encoding, errors="replace")
        except LookupError:
            pass
    return data.decode("utf-8", errors="replace")


def run_process(args: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> ProcessResult:
    """Run ``args`` without a shell and capture its output.

    Output is captured as bytes and decoded with :func:`decode_console_bytes`
    so localized console tools can never crash the reader with a codec error.
    Timeouts and spawn errors surface as exceptions which
    :func:`guard_exceptions` converts into a ``ToolResult``.
    """
    completed = subprocess.run(
        list(args),
        capture_output=True,  # bytes; decoded manually below
        timeout=timeout,
        creationflags=_CREATION_FLAGS,
    )
    return ProcessResult(
        returncode=completed.returncode,
        stdout=decode_console_bytes(completed.stdout or b""),
        stderr=decode_console_bytes(completed.stderr or b""),
    )


def guard_exceptions(fn, **kwargs) -> ToolResult:
    """Run ``fn(**kwargs)`` and convert expected failures into ToolResult.

    This is the single place where worker-thread exceptions become
    user-readable tool failures instead of crashing the application.
    """
    from wynes.core.i18n import tr

    try:
        return fn(**kwargs)
    except subprocess.TimeoutExpired:
        return ToolResult(
            status=ToolStatus.TIMEOUT,
            summary=tr("state.timeout.summary"),
            error=tr("state.timeout.detail"),
        )
    except PermissionError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary=tr("error.permission.summary"),
            error=str(exc),
        )
    except FileNotFoundError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary=tr("error.missing_executable.summary"),
            error=tr("error.missing_executable.detail", detail=str(exc)),
        )
    except OSError as exc:
        return ToolResult(
            status=ToolStatus.ERROR,
            summary=tr("error.os.summary"),
            error=str(exc),
        )
    except Exception as exc:  # last line of defence: report, never crash
        return ToolResult(
            status=ToolStatus.ERROR,
            summary=tr("error.unexpected.summary"),
            error=f"{type(exc).__name__}: {exc}",
        )
