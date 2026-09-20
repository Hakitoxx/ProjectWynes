"""Local system information.

Collects basic facts about the local machine using the standard library
(plus two read-only Windows kernel calls for memory and uptime). Nothing
leaves the machine; no elevated privileges are required.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import platform
import sys

from wynes import __version__
from wynes.core.i18n import tr
from wynes.core.tool_base import Availability, Tool, ToolResult, ToolStatus


def _memory_info() -> tuple:
    """Return (total_bytes, available_bytes) or ("", "") when unknown."""
    if sys.platform.startswith("win"):
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.wintypes.DWORD),
                    ("dwMemoryLoad", ctypes.wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.ullTotalPhys, status.ullAvailPhys
        except OSError:
            pass
    else:  # POSIX fallback
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return pages * page_size, 0
        except (ValueError, OSError, AttributeError):
            pass
    return "", ""


def _uptime_seconds():
    if sys.platform.startswith("win"):
        try:
            return ctypes.windll.kernel32.GetTickCount64() // 1000
        except OSError:
            return None
    try:
        with open("/proc/uptime", "r", encoding="ascii") as handle:
            return int(float(handle.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def _format_uptime(seconds) -> str:
    if seconds is None:
        return tr("sysinfo.unknown")
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return tr("sysinfo.uptime_format", days=days, hours=hours, minutes=minutes)


def _format_gib(num_bytes) -> str:
    if num_bytes in ("", None):
        return tr("sysinfo.unknown")
    return f"{num_bytes / (1024 ** 3):.1f} GiB"


class SystemInfoTool(Tool):
    name_key = "tool.sysinfo.name"
    description_key = "tool.sysinfo.description"
    category_key = "category.system"
    version = "1.0"
    auto_run = True

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.sysinfo.available")

    def run(self, **_inputs) -> ToolResult:
        try:
            return self._collect()
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("state.error"),
                error=f"{type(exc).__name__}: {exc}",
            )

    def _collect(self) -> ToolResult:
        total_mem, avail_mem = _memory_info()

        os_rows = [
            (tr("sysinfo.os"), f"{platform.system()} {platform.release()}"),
            (tr("sysinfo.os_version"), platform.version()),
            (tr("sysinfo.architecture"), platform.machine()),
            (tr("sysinfo.hostname"), platform.node() or tr("sysinfo.unknown")),
        ]
        if sys.platform.startswith("win"):
            win_ver = platform.win32_ver()
            if win_ver and win_ver[0]:
                os_rows.append((tr("sysinfo.windows_edition"), win_ver[0]))

        cpu_name = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "")
        hardware_rows = [
            (tr("sysinfo.cpu"), cpu_name or tr("sysinfo.unknown")),
            (tr("sysinfo.cpu_cores"), str(os.cpu_count() or tr("sysinfo.unknown"))),
            (tr("sysinfo.memory_total"), _format_gib(total_mem)),
        ]
        if avail_mem != "":
            hardware_rows.append((tr("sysinfo.memory_available"), _format_gib(avail_mem)))

        runtime_rows = [
            (tr("sysinfo.python"), platform.python_version()),
            (tr("sysinfo.platform"), sys.platform),
            (tr("sysinfo.wynes_version"), __version__),
            (tr("sysinfo.uptime"), _format_uptime(_uptime_seconds())),
        ]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("sysinfo.summary", host=platform.node() or "-"),
            data=[
                (tr("sysinfo.section.os"), os_rows),
                (tr("sysinfo.section.hardware"), hardware_rows),
                (tr("sysinfo.section.runtime"), runtime_rows),
            ],
        )
