"""Tool registry.

Every tool that exists in the application — ready, planned, or waiting for
an external dependency — is registered in :data:`ALL_TOOLS`. The dashboard
and navigation read from this registry, so adding a tool later means:
create one module, then either add it here or flip ``planned=True`` off.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from wynes.core.tool_base import Availability, Tool
from wynes.tools.dns_lookup import DnsLookupTool


class PlannedTool(Tool):
    """Entry for a tool that is scheduled but not implemented yet.

    Shown in the navigation and dashboard as "Planned"; its page explains
    the status instead of pretending the feature exists.
    """

    offline = False
    planned_note: str = ""

    def __init__(self, name: str, description: str, category: str) -> None:
        self.name = name
        self.description = description
        self.category = category
        self.planned_note = description

    def availability(self) -> tuple:
        return Availability.UNKNOWN, "Planned — not implemented yet"

    def run(self, **inputs):  # pragma: no cover - UI blocks execution
        raise NotImplementedError("This tool is planned but not implemented yet.")


ALL_TOOLS: list = [
    DnsLookupTool(),
    PlannedTool("Ping", "ICMP echo diagnostics via the system ping utility.", "Network"),
    PlannedTool("Traceroute", "Trace the network path to a host (OS tracert/traceroute).", "Network"),
    PlannedTool("Port Check", "Check TCP port reachability on authorized hosts.", "Network"),
    PlannedTool("HTTP Headers", "Retrieve and inspect HTTP response headers.", "Web"),
    PlannedTool("TLS / Certificate Info", "Inspect TLS certificate details of a host.", "Web"),
    PlannedTool("File Hash", "Compute SHA-256 and other digests of local files.", "System"),
    PlannedTool("Process List", "List running processes with basic details.", "System"),
    PlannedTool("Nmap Scan", "Port/service discovery via the official Nmap CLI.", "External"),
]


@dataclass(frozen=True)
class ToolEntry:
    tool: Tool
    availability: Availability
    detail: str
    planned: bool


class ToolManager:
    """Provides tool instances and caches their availability state."""

    def __init__(self) -> None:
        self._status: dict = {}

    def all_entries(self) -> list:
        return [self.entry_for(tool) for tool in ALL_TOOLS]

    def entry_for(self, tool: Tool) -> ToolEntry:
        if tool not in self._status:
            try:
                availability, detail = tool.availability()
            except Exception as exc:  # defensive: a broken check must not break the app
                availability, detail = Availability.UNKNOWN, f"Check failed: {exc}"
            planned = isinstance(tool, PlannedTool)
            self._status[tool] = ToolEntry(tool=tool, availability=availability,
                                           detail=detail, planned=planned)
        return self._status[tool]

    def ensure_ready(self, tool: Tool) -> Optional[str]:
        """Return an error message if the tool must not run, else ``None``."""
        entry = self.entry_for(tool)
        if entry.planned:
            return "This tool is planned but not implemented yet."
        if entry.availability is Availability.MISSING:
            return f"Unavailable: {entry.detail}"
        return None
