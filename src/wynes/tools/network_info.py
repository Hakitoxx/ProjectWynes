"""Local network adapter information.

Primary source on Windows is a single read-only PowerShell query
(``Get-NetAdapter``/``Get-NetIPAddress``/``Get-DnsClientServerAddress``/
``Get-NetRoute``) returned as JSON — property names are locale
independent, which makes parsing robust on any display language. If
PowerShell is unavailable, a socket-only fallback still reports the host
name and resolvable addresses.

Everything stays local; no network traffic is generated.
"""
from __future__ import annotations

import json
import socket
import sys

from wynes.core.i18n import tr
from wynes.core.process import run_process
from wynes.core.tool_base import Availability, Tool, ToolResult, ToolStatus

_PS_SCRIPT = (
    "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
    "$ErrorActionPreference='SilentlyContinue'; "
    "$result = [ordered]@{"
    "Adapters = @(Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed); "
    "Addresses = @(Get-NetIPAddress | Select-Object InterfaceAlias, AddressFamily, IPAddress, PrefixLength); "
    "Dns = @(Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses); "
    "Gateways = @(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object InterfaceAlias, NextHop, RouteMetric)"
    "}; "
    "$result | ConvertTo-Json -Depth 4 -Compress"
)


def _as_list(value) -> list:
    """PowerShell unwraps single-element arrays; normalize back to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def query_windows_network() -> dict:
    """Run the read-only PowerShell query and return the parsed object."""
    completed = run_process(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
        timeout=45,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("PowerShell network query failed")
    return json.loads(completed.stdout)


class NetworkInfoTool(Tool):
    name_key = "tool.netinfo.name"
    description_key = "tool.netinfo.description"
    category_key = "category.system"
    version = "1.0"
    auto_run = True

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.netinfo.available")

    def run(self, **_inputs) -> ToolResult:
        if sys.platform.startswith("win"):
            try:
                return self._render_windows(query_windows_network())
            except Exception:
                # fall through to the socket-only fallback below
                pass
        return self._render_fallback()

    # ------------------------------------------------------------- renderers
    def _render_windows(self, info: dict) -> ToolResult:
        adapters = _as_list(info.get("Adapters"))
        addresses = _as_list(info.get("Addresses"))
        dns_entries = _as_list(info.get("Dns"))
        gateways = _as_list(info.get("Gateways"))

        by_interface_4: dict = {}
        by_interface_6: dict = {}
        for entry in addresses:
            alias = entry.get("InterfaceAlias", "")
            family = entry.get("AddressFamily", "")
            if not isinstance(family, str) or not family.startswith("IPv"):
                family = {2: "IPv4", 23: "IPv6"}.get(entry.get("AddressFamily"), "?")
            text = f"{entry.get('IPAddress', '')}/{entry.get('PrefixLength', '')}"
            bucket = by_interface_4 if family == "IPv4" else by_interface_6
            bucket.setdefault(alias, []).append(text)

        dns_by_interface = {
            entry.get("InterfaceAlias", ""): ", ".join(
                _as_list(entry.get("ServerAddresses"))
            )
            for entry in dns_entries
        }
        gateway_by_interface = {
            entry.get("InterfaceAlias", ""): entry.get("NextHop", "")
            for entry in gateways
            if entry.get("NextHop")
        }

        data = [(tr("netinfo.section.host"), [
            (tr("sysinfo.hostname"), socket.gethostname()),
            (tr("netinfo.adapter_count"), str(len(adapters))),
        ])]

        for index, adapter in enumerate(adapters, start=1):
            name = adapter.get("Name", f"#{index}")
            rows = [
                (tr("netinfo.description"), adapter.get("InterfaceDescription", "") or "-"),
                (tr("netinfo.state"), adapter.get("Status", "")),
                (tr("netinfo.mac"), adapter.get("MacAddress", "") or "-"),
                (tr("netinfo.speed"), str(adapter.get("LinkSpeed", "") or "-")),
            ]
            ipv4 = by_interface_4.get(name, [])
            ipv6 = by_interface_6.get(name, [])
            if ipv4:
                rows.append((tr("netinfo.ipv4"), ", ".join(ipv4)))
            if ipv6:
                rows.append((tr("netinfo.ipv6"), ", ".join(ipv6)))
            if dns_by_interface.get(name):
                rows.append((tr("netinfo.dns_servers"), dns_by_interface[name]))
            if gateway_by_interface.get(name):
                rows.append((tr("netinfo.gateway"), gateway_by_interface[name]))
            data.append((f"{name}", rows))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("netinfo.summary", count=len(adapters)),
            data=data,
        )

    def _render_fallback(self) -> ToolResult:
        hostname = socket.gethostname()
        rows = [(tr("sysinfo.hostname"), hostname)]
        try:
            infos = socket.getaddrinfo(hostname, None)
            addresses = sorted({info[4][0] for info in infos})
            if addresses:
                rows.append((tr("netinfo.addresses"), ", ".join(addresses)))
        except socket.gaierror:
            pass
        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("netinfo.summary_fallback"),
            data=[(tr("netinfo.section.host"), rows)],
            error=tr("netinfo.fallback_note"),
        )
