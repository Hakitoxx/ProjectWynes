"""Traceroute diagnostic tool.

Uses the operating system's ``tracert`` (Windows) / ``traceroute`` (POSIX)
executable with safe argument lists. Output parsing is locale-independent
and structural: hop lines start with a hop number and contain timing
samples (``<1 ms``, ``23 ms``) or ``*`` for missed probes, followed by the
hop address or ``hostname [ip]``.
"""
from __future__ import annotations

import re
import sys
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
from wynes.core.validators import normalize_target, validate_target

_MAX_HOPS_LIMIT = 30

_HOP_LINE_RE = re.compile(r"^\s*(\d{1,2})\s+(.*)$")
_SAMPLE_RE = re.compile(r"<\s*(\d+)\s*ms|(\d+)\s*ms|(\*)")
_HOST_WITH_IP_RE = re.compile(r"^(?P<host>.*?)\s*\[(?P<ip>[0-9a-fA-F:.]+)\]\s*$")
#: a real address token (IP or host name) never contains whitespace —
#: lines like "Request timed out." (localized) are therefore ignored safely
_ADDRESS_TOKEN_RE = re.compile(r"^[A-Za-z0-9.:_-]+$")


@dataclass
class Hop:
    number: int
    times_ms: list = field(default_factory=list)
    missed: int = 0
    host: str = ""
    ip: str = ""


def build_traceroute_args(target: str, max_hops: int, timeout_ms: int, resolve_names: bool) -> list:
    """Build the platform-appropriate traceroute command as an argument list."""
    if sys.platform.startswith("win"):
        args = ["tracert", "-h", str(max_hops), "-w", str(timeout_ms)]
        if not resolve_names:
            args.append("-d")
        return args + [target]
    args = ["traceroute", "-m", str(max_hops), "-w", str(max(1, timeout_ms // 1000))]
    if not resolve_names:
        args.append("-n")
    return args + [target]


def parse_traceroute_output(text: str) -> list:
    """Parse hop lines from tracert/traceroute output into :class:`Hop` items."""
    hops: list = []
    for line in text.splitlines():
        match = _HOP_LINE_RE.match(line)
        if not match:
            continue
        number = int(match.group(1))
        if number > _MAX_HOPS_LIMIT:
            continue
        rest = match.group(2)
        hop = Hop(number=number)

        # remove timing samples and asterisks; what remains is the address
        for sample in _SAMPLE_RE.finditer(rest):
            if sample.group(3) is not None:
                hop.missed += 1
            else:
                value = sample.group(1) or sample.group(2)
                hop.times_ms.append(int(value))
        address_part = _SAMPLE_RE.sub(" ", rest).strip()
        with_ip = _HOST_WITH_IP_RE.match(address_part) if address_part else None
        if with_ip:
            hop.host = with_ip.group("host").strip()
            hop.ip = with_ip.group("ip")
        elif address_part and _ADDRESS_TOKEN_RE.match(address_part):
            hop.ip = address_part
        # anything else ("Request timed out." in any language) = no address
        hops.append(hop)
    return hops


class TracerouteTool(Tool):
    name_key = "tool.traceroute.name"
    description_key = "tool.traceroute.description"
    category_key = "category.network"
    version = "1.0"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.traceroute.field.target.label",
            placeholder_key="tool.traceroute.field.target.placeholder",
        ),
        InputField(
            key="hops",
            label_key="tool.traceroute.field.hops.label",
            kind="number",
            default=20,
            minimum=1,
            maximum=_MAX_HOPS_LIMIT,
        ),
        InputField(
            key="resolve",
            label_key="tool.traceroute.field.resolve.label",
            kind="checkbox",
            default=True,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.traceroute.available")

    def validate(self, **inputs) -> list:
        return validate_target(inputs.get("target", ""))

    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        try:
            max_hops = int(inputs.get("hops", 20))
        except (TypeError, ValueError):
            max_hops = 20
        max_hops = max(1, min(_MAX_HOPS_LIMIT, max_hops))
        resolve = bool(inputs.get("resolve", True))
        timeout_ms = 1000

        args = build_traceroute_args(target, max_hops, timeout_ms, resolve)
        total_timeout = max_hops * 3 * (timeout_ms // 1000) + 30
        proc = run_process(args, timeout=total_timeout)

        hops = parse_traceroute_output(proc.stdout)
        table_rows = []
        for hop in hops:
            if hop.times_ms:
                times = "  ".join(tr("fmt.ms", value=value) for value in hop.times_ms)
            else:
                times = tr("traceroute.no_response")
            display_address = hop.host or hop.ip or tr("traceroute.unknown")
            if hop.host and hop.ip:
                display_address = f"{hop.host} [{hop.ip}]"
            table_rows.append((str(hop.number), display_address, times))

        tables = []
        if table_rows:
            tables.append(TableData(
                title=tr("traceroute.section.hops"),
                columns=(tr("traceroute.col.hop"), tr("traceroute.col.address"),
                         tr("traceroute.col.times")),
                rows=table_rows,
            ))

        reached = False
        if hops:
            last = hops[-1]
            reached = bool(last.ip or last.host) and bool(last.times_ms)

        return ToolResult(
            status=ToolStatus.SUCCESS if hops else ToolStatus.ERROR,
            summary=tr("traceroute.summary", hops=len(hops), target=target) if hops
            else tr("traceroute.failed_summary", target=target),
            data=[(tr("traceroute.section.trace"), [
                (tr("ping.target"), target),
                (tr("traceroute.hops_count"), str(len(hops))),
            ])],
            tables=tables,
            raw_output=proc.stdout.strip(),
            error="" if hops else tr("traceroute.failed_detail"),
        )
