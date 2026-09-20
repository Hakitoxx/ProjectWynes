"""Local process inspection (read-only).

Windows: enumerates processes via the Toolhelp snapshot API and enriches
each entry with its executable path and working-set memory via
``OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)``. Processes that refuse
access (protected/system processes without elevation) are counted and
reported transparently instead of failing.
POSIX fallback: parses ``ps`` output.

This tool is strictly observational: no termination, injection or
modification — by design.
"""
from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    TableData,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.tools.file_hash import format_size

_MAX_DISPLAY_ROWS = 500


@dataclass
class ProcessEntry:
    pid: int
    name: str
    memory_kb: object = None  # None when access was denied
    path: str = ""


# ------------------------------------------------------------------ Windows
if sys.platform.startswith("win"):
    import ctypes.wintypes as _wt

    _kernel32 = ctypes.windll.kernel32
    _psapi = ctypes.windll.psapi

    _TH32CS_SNAPPROCESS = 0x00000002
    _INVALID_HANDLE = _wt.HANDLE(-1).value
    _QUERY_LIMITED = 0x1000

    class _PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", _wt.DWORD),
            ("cntUsage", _wt.DWORD),
            ("th32ProcessID", _wt.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", _wt.DWORD),
            ("cntThreads", _wt.DWORD),
            ("th32ParentProcessID", _wt.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", _wt.DWORD),
            ("szExeFile", _wt.WCHAR * 260),
        ]

    class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", _wt.DWORD),
            ("PageFaultCount", _wt.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    def _enrich(pid: int) -> tuple:
        """Return (path, memory_kb); empty when access is denied."""
        handle = _kernel32.OpenProcess(_QUERY_LIMITED, False, pid)
        if not handle:
            return "", None
        try:
            path = ""
            memory_kb = None
            buffer = ctypes.create_unicode_buffer(1024)
            size = _wt.DWORD(len(buffer))
            if _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                path = buffer.value
            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
            if _psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            ):
                memory_kb = counters.WorkingSetSize // 1024
            return path, memory_kb
        finally:
            _kernel32.CloseHandle(handle)

    def _list_windows() -> list:
        snapshot = _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if snapshot == _INVALID_HANDLE:
            raise OSError("CreateToolhelp32Snapshot failed")
        entries = []
        try:
            entry = _PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
            ok = _kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                pid = entry.th32ProcessID
                if pid > 0:
                    path, memory_kb = _enrich(pid)
                    entries.append(ProcessEntry(pid, entry.szExeFile, memory_kb, path))
                ok = _kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            _kernel32.CloseHandle(snapshot)
        return entries


def _list_posix() -> list:
    from wynes.core.process import run_process

    proc = run_process(["ps", "-eo", "pid=,comm=,rss="], timeout=15)
    entries = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
            rss_kb = int(parts[2]) if len(parts) > 2 else None
        except ValueError:
            continue
        entries.append(ProcessEntry(pid, parts[1], rss_kb, ""))
    return entries


def list_processes() -> list:
    """Return all visible :class:`ProcessEntry` objects, sorted by name."""
    if sys.platform.startswith("win"):
        entries = _list_windows()
    else:
        entries = _list_posix()
    entries.sort(key=lambda entry: entry.name.lower())
    return entries


class ProcessListTool(Tool):
    name_key = "tool.process.name"
    description_key = "tool.process.description"
    category_key = "category.system"
    version = "1.0"
    auto_run = True
    input_fields = (
        InputField(
            key="filter",
            label_key="tool.process.field.filter.label",
            placeholder_key="tool.process.field.filter.placeholder",
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.process.available")

    def run(self, **inputs) -> ToolResult:
        try:
            entries = list_processes()
        except OSError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("process.error"),
                error=str(exc),
            )

        text_filter = str(inputs.get("filter", "")).strip().lower()
        if text_filter:
            entries = [entry for entry in entries
                       if text_filter in entry.name.lower()
                       or text_filter in entry.path.lower()
                       or text_filter == str(entry.pid)]

        restricted = sum(1 for entry in entries if entry.memory_kb is None)
        shown = entries[:_MAX_DISPLAY_ROWS]

        rows = []
        for entry in shown:
            memory = (
                format_size(entry.memory_kb * 1024)
                if entry.memory_kb is not None
                else tr("process.access_denied")
            )
            rows.append((str(entry.pid), entry.name, memory, entry.path or "—"))

        columns = (
            tr("process.col.pid"), tr("process.col.name"),
            tr("process.col.memory"), tr("process.col.path"),
        )
        tables = [TableData(
            title=tr("process.section.table", shown=len(shown), total=len(entries)),
            columns=columns,
            rows=rows,
        )]

        summary_rows = [
            (tr("process.total"), str(len(entries))),
        ]
        if restricted:
            summary_rows.append(
                (tr("process.restricted_count"), tr("process.restricted_note", count=restricted))
            )

        raw_lines = ["pid\tname\tmemory_kb\tpath"]
        raw_lines += [
            f"{e.pid}\t{e.name}\t{e.memory_kb if e.memory_kb is not None else ''}\t{e.path}"
            for e in shown
        ]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("process.summary", count=len(entries)),
            data=[(tr("process.section.summary"), summary_rows)],
            tables=tables,
            raw_output="\n".join(raw_lines),
        )
