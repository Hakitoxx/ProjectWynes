"""Ping diagnostic tool.

Uses the operating system's ``ping`` executable with safe argument lists.
Output parsing is deliberately locale-independent: ping prints localized
text on many systems (e.g. a Turkish Windows prints Turkish text), so the
parser relies only on stable protocol markers — replies contain ``TTL=``,
timings end in ``ms``, and the resolved address appears in brackets.

No raw sockets, no elevated privileges required.
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
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import normalize_target, validate_target

_REPLY_MARKER = "TTL="
_TIME_RE = re.compile(r"<\s*(\d+)\s*ms|(\d+)\s*ms")
_BRACKET_IP_RE = re.compile(r"\[([0-9a-fA-F.:]+)\]")


@dataclass
class PingStats:
    replies: int = 0
    times_ms: list = field(default_factory=list)
    resolved_ip: str = ""


def build_ping_args(target: str, count: int, timeout_ms: int) -> list:
    """Build the platform-appropriate ping command as an argument list."""
    if sys.platform.startswith("win"):
        return ["ping", "-n", str(count), "-w", str(timeout_ms), target]
    # POSIX: -c count, -W per-reply timeout in seconds (minimum 1)
    wait_seconds = max(1, int(round(timeout_ms / 1000)))
    return ["ping", "-c", str(count), "-W", str(wait_seconds), target]


def parse_ping_output(text: str, requested: int) -> PingStats:
    """Extract reply count, timings and resolved address from ping output."""
    stats = PingStats()
    for line in text.splitlines():
        bracket = _BRACKET_IP_RE.search(line)
        if bracket and not stats.resolved_ip:
            stats.resolved_ip = bracket.group(1)
        if _REPLY_MARKER in line or _REPLY_MARKER.lower() in line.lower():
            stats.replies += 1
            for match in _TIME_RE.finditer(line):
                value = match.group(1) if match.group(1) is not None else match.group(2)
                stats.times_ms.append(int(value))
    return stats


class PingTool(Tool):
    name_key = "tool.ping.name"
    description_key = "tool.ping.description"
    category_key = "category.network"
    version = "1.0"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.ping.field.target.label",
            placeholder_key="tool.ping.field.target.placeholder",
        ),
        InputField(
            key="count",
            label_key="tool.ping.field.count.label",
            kind="number",
            default=4,
            minimum=1,
            maximum=20,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.ping.available")

    def validate(self, **inputs) -> list:
        return validate_target(inputs.get("target", ""))

    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        try:
            count = int(inputs.get("count", 4))
        except (TypeError, ValueError):
            count = 4
        count = max(1, min(20, count))
        timeout_ms = 1000

        args = build_ping_args(target, count, timeout_ms)
        total_timeout = (count * timeout_ms // 1000) + 15
        proc = run_process(args, timeout=total_timeout)

        stats = parse_ping_output(proc.stdout + "\n" + proc.stderr, count)
        loss = max(0, count - stats.replies)

        data = [(tr("ping.section.target"), [(tr("ping.target"), target)])]
        if stats.resolved_ip and stats.resolved_ip != target:
            data[0][1].append((tr("ping.resolved_ip"), stats.resolved_ip))
        data.append((
            tr("ping.section.packets"),
            [
                (tr("ping.sent"), str(count)),
                (tr("ping.received"), str(stats.replies)),
                (tr("ping.lost"), str(loss)),
            ],
        ))
        if stats.times_ms:
            data.append((
                tr("ping.section.times"),
                [
                    (tr("ping.time_min"), tr("fmt.ms", value=min(stats.times_ms))),
                    (tr("ping.time_max"), tr("fmt.ms", value=max(stats.times_ms))),
                    (
                        tr("ping.time_avg"),
                        tr("fmt.ms", value=round(sum(stats.times_ms) / len(stats.times_ms), 1)),
                    ),
                ],
            ))

        reachable = stats.replies > 0
        return ToolResult(
            status=ToolStatus.SUCCESS if reachable else ToolStatus.ERROR,
            summary=tr("ping.reachable", target=target) if reachable
            else tr("ping.unreachable", target=target),
            data=data,
            raw_output=proc.stdout.strip(),
            error="" if reachable else tr("ping.unreachable_detail"),
        )
