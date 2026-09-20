"""TCP port check tool.

Performs a single TCP connect to one host and one port — a connectivity
diagnostic, not a port scanner. No raw sockets, no privileges required.
"""
from __future__ import annotations

import socket
import time

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import (
    normalize_target,
    validate_port,
    validate_target,
)


class PortCheckTool(Tool):
    name_key = "tool.port.name"
    description_key = "tool.port.description"
    category_key = "category.network"
    version = "1.0"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.port.field.target.label",
            placeholder_key="tool.port.field.target.placeholder",
        ),
        InputField(
            key="port",
            label_key="tool.port.field.port.label",
            kind="number",
            default=443,
            minimum=1,
            maximum=65535,
        ),
        InputField(
            key="timeout",
            label_key="tool.port.field.timeout.label",
            kind="number",
            default=3,
            minimum=1,
            maximum=30,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.port.available")

    def validate(self, **inputs) -> list:
        errors = validate_target(inputs.get("target", ""))
        errors += validate_port(inputs.get("port", ""))
        return errors

    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        port = int(inputs.get("port", 443))
        try:
            timeout = float(inputs.get("timeout", 3))
        except (TypeError, ValueError):
            timeout = 3.0
        timeout = min(30.0, max(1.0, timeout))

        service = ""
        try:
            service = socket.getservbyport(port, "tcp")
        except (OSError, OverflowError):
            pass

        started = time.perf_counter()
        sock = None
        try:
            sock = socket.create_connection((target, port), timeout=timeout)
            elapsed_ms = (time.perf_counter() - started) * 1000
            peer_ip = sock.getpeername()[0]
        except (ConnectionRefusedError, OSError) as exc:
            return self._failure(target, port, service, exc)
        finally:
            if sock is not None:
                sock.close()

        rows = [
            (tr("port.col_target"), f"{target}:{port}"),
            (tr("port.state"), tr("port.state_open")),
            (tr("port.response_time"), tr("fmt.ms", value=round(elapsed_ms, 1))),
        ]
        if peer_ip and peer_ip != target:
            rows.append((tr("ping.resolved_ip"), peer_ip))
        if service:
            rows.append((tr("port.service"), service))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("port.open_summary", target=target, port=port),
            data=[(tr("port.section.result"), rows)],
        )

    def _failure(self, target: str, port: int, service: str, exc: OSError) -> ToolResult:
        if isinstance(exc, socket.gaierror):
            state_key = "port.state_dns_error"
            summary = tr("port.dns_error", target=target)
        elif isinstance(exc, (socket.timeout, TimeoutError)):
            state_key = "port.state_filtered"
            summary = tr("port.timeout_summary", target=target, port=port)
        elif isinstance(exc, ConnectionRefusedError):
            state_key = "port.state_closed"
            summary = tr("port.closed_summary", target=target, port=port)
        else:
            state_key = "port.state_unreachable"
            summary = tr("port.error_summary", target=target, port=port)

        rows = [
            (tr("port.col_target"), f"{target}:{port}"),
            (tr("port.state"), tr(state_key)),
        ]
        if service:
            rows.append((tr("port.service"), service))

        return ToolResult(
            status=ToolStatus.ERROR,
            summary=summary,
            data=[(tr("port.section.result"), rows)],
            error=tr("port.error_detail", reason=_friendly_reason(exc)),
        )


def _friendly_reason(exc: OSError) -> str:
    """Short, non-technical reason text (no raw tracebacks)."""
    reason = getattr(exc, "strerror", None) or str(exc)
    return reason.split("\n")[0].strip()[:200]
