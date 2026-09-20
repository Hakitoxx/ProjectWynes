"""Tool registry.

Every diagnostic tool is created by :func:`build_tools`. The dashboard and
navigation read from this registry, so adding a tool later means: create
its module under ``wynes/tools/`` and add one line here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from wynes.core.tool_base import Availability, Tool
from wynes.tools.dns_lookup import DnsLookupTool
from wynes.tools.file_hash import FileHashTool
from wynes.tools.http_headers import HttpHeadersTool
from wynes.tools.network_info import NetworkInfoTool
from wynes.tools.nmap_scan import NmapScanTool
from wynes.tools.ping import PingTool
from wynes.tools.port_check import PortCheckTool
from wynes.tools.process_list import ProcessListTool
from wynes.tools.system_info import SystemInfoTool
from wynes.tools.tls_info import TlsInfoTool
from wynes.tools.traceroute import TracerouteTool


def build_tools() -> list:
    """Create fresh tool instances in sidebar order."""
    return [
        # Network
        DnsLookupTool(),
        PingTool(),
        TracerouteTool(),
        PortCheckTool(),
        HttpHeadersTool(),
        TlsInfoTool(),
        NmapScanTool(),
        # System
        SystemInfoTool(),
        NetworkInfoTool(),
        ProcessListTool(),
        # Files
        FileHashTool(),
    ]


@dataclass(frozen=True)
class ToolEntry:
    tool: Tool
    availability: Availability
    detail: str

    @property
    def ready(self) -> bool:
        return self.availability is Availability.READY


class ToolManager:
    """Provides tool instances and caches their availability state.

    The cache is keyed by tool class and is invalidated on language
    changes so localized detail texts stay current.
    """

    def __init__(self) -> None:
        self.tools: list = build_tools()
        self._status: dict = {}

    def all_entries(self) -> list:
        return [self.entry_for(tool) for tool in self.tools]

    def entry_for(self, tool: Tool) -> ToolEntry:
        key = type(tool)
        if key not in self._status:
            try:
                availability, detail = tool.availability()
            except Exception as exc:  # defensive: a broken check must not break the app
                availability, detail = Availability.UNKNOWN, f"Check failed: {exc}"
            self._status[key] = ToolEntry(tool=tool, availability=availability, detail=detail)
        return self._status[key]

    def ensure_ready(self, tool: Tool) -> Optional[str]:
        """Return an error message if the tool must not run, else ``None``."""
        entry = self.entry_for(tool)
        if entry.availability is not Availability.READY:
            return entry.detail
        return None

    def clear_cache(self) -> None:
        self._status.clear()
