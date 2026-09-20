"""Nmap integration — defensive, authorized diagnostics.

The official Nmap executable is detected (PATH -> installer defaults ->
user-configured path in Settings), its version is read, and strictly
limited scan profiles are executed with argument lists (never a shell),
timeouts, and full output capture.

Deliberately not supported: exploit scripts, brute force, evasion/stealth
flags, OS fingerprinting (needs admin), broad CIDR ranges (> /24).
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field

from wynes.core.i18n import tr
from wynes.core.process import run_process
from wynes.core.tool_base import (
    Availability,
    InputField,
    TableData,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import normalize_target, sanitize_nmap_target

#: Default install locations of the official Nmap Windows installer.
_DEFAULT_LOCATIONS = (
    r"C:\Program Files (x86)\Nmap\nmap.exe",
    r"C:\Program Files\Nmap\nmap.exe",
)

SCAN_TIMEOUT_S = 300

SCAN_PROFILES: dict = {
    "discover": ["-sn", "-T3"],
    "quick": ["-sT", "--top-ports", "100", "-T3"],
    "services": ["-sT", "-sV", "--version-light", "--top-ports", "100", "-T3"],
}

_PORT_LINE_RE = re.compile(r"^(\d{1,5})/(tcp|udp)\s+(\S+)\s+(.*\S)\s*$")
_REPORT_RE = re.compile(r"^Nmap scan report for (.+)$")
_VERSION_RE = re.compile(r"Nmap version (\S+)")


# --------------------------------------------------------------- detection
def find_nmap_executable() -> str:
    """Return the Nmap executable path or "" when not found.

    Order: user-configured path (Settings) -> PATH -> installer defaults.
    """
    from wynes.core import settings

    configured = str(settings.get_value("nmap/path", "") or "").strip()
    if configured and os.path.isfile(configured):
        return configured
    on_path = shutil.which("nmap")
    if on_path:
        return on_path
    for candidate in _DEFAULT_LOCATIONS:
        if os.path.isfile(candidate):
            return candidate
    return ""


def nmap_version(path: str) -> str:
    """Return the Nmap version string ("" on failure)."""
    if not path:
        return ""
    try:
        proc = run_process([path, "--version"], timeout=15)
    except Exception:
        return ""
    match = _VERSION_RE.search(proc.stdout)
    return match.group(1) if match else ""


# ------------------------------------------------------------------ parsing
@dataclass
class HostScan:
    host: str
    up: bool = True
    ports: list = field(default_factory=list)  # (port, proto, state, service)


def parse_nmap_output(text: str) -> list:
    """Parse standard Nmap text output into per-host results."""
    hosts: list = []
    current = None
    for line in text.splitlines():
        report = _REPORT_RE.match(line.strip())
        if report:
            current = HostScan(host=report.group(1).strip())
            hosts.append(current)
            continue
        if current is None:
            continue
        if "Host seems down" in line:
            current.up = False
            continue
        port_match = _PORT_LINE_RE.match(line.strip())
        if port_match:
            current.ports.append((
                f"{port_match.group(1)}/{port_match.group(2)}",
                port_match.group(3),
                port_match.group(4).strip(),
            ))
    return hosts


# --------------------------------------------------------------------- tool
class NmapScanTool(Tool):
    name_key = "tool.nmap.name"
    description_key = "tool.nmap.description"
    category_key = "category.network"
    version = "1.0"
    notice_key = "nmap.page.notice"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.nmap.field.target.label",
            placeholder_key="tool.nmap.field.target.placeholder",
        ),
        InputField(
            key="profile",
            label_key="tool.nmap.field.profile.label",
            kind="choice",
            default="quick",
            options=(
                ("discover", "nmap.profile.discover"),
                ("quick", "nmap.profile.quick"),
                ("services", "nmap.profile.services"),
            ),
        ),
    )

    def availability(self) -> tuple:
        path = find_nmap_executable()
        if not path:
            return Availability.MISSING, tr("nmap.missing.detail")
        version = nmap_version(path) or tr("nmap.version_unknown")
        return Availability.READY, tr("nmap.ready.detail", version=version, path=path)

    def validate(self, **inputs) -> list:
        errors = sanitize_nmap_target(inputs.get("target", ""))
        profile = inputs.get("profile", "quick")
        if profile not in SCAN_PROFILES:
            from wynes.core.tool_base import ValidationError

            errors.append(ValidationError(tr("nmap.invalid_profile"), field="profile"))
        return errors

    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        profile = str(inputs.get("profile", "quick"))
        args_profile = SCAN_PROFILES.get(profile, SCAN_PROFILES["quick"])

        path = find_nmap_executable()
        if not path:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("nmap.missing.summary"),
                error=tr("nmap.missing.detail"),
            )

        proc = run_process([path, *args_profile, target], timeout=SCAN_TIMEOUT_S)
        hosts = parse_nmap_output(proc.stdout)

        if not hosts:
            message = proc.stderr.strip() or proc.stdout.strip()
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("nmap.no_results", target=target),
                error=tr("nmap.no_results_detail"),
                raw_output=(proc.stdout + "\n" + proc.stderr).strip(),
            )

        up_count = sum(1 for host in hosts if host.up)
        open_ports = [
            (host, port) for host in hosts for port in host.ports
            if port[1] == "open"
        ]

        tables = []
        columns = (
            tr("nmap.col.port"), tr("nmap.col.state"), tr("nmap.col.service"),
        )
        for host in hosts:
            if host.ports:
                tables.append(TableData(
                    title=host.host,
                    columns=columns,
                    rows=[(port[0], port[1], port[2]) for port in host.ports],
                ))

        rows = [
            (tr("nmap.target"), target),
            (tr("nmap.profile_label"), tr(f"nmap.profile.{profile}")),
            (tr("nmap.hosts_found"), str(len(hosts))),
            (tr("nmap.hosts_up"), str(up_count)),
            (tr("nmap.open_ports"), str(len(open_ports))),
        ]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("nmap.summary", hosts=up_count, ports=len(open_ports)),
            data=[(tr("nmap.section.scan"), rows)],
            tables=tables,
            raw_output=proc.stdout.strip(),
        )
