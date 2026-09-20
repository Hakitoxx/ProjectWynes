"""DNS lookup tool.

Resolves host names to IPv4/IPv6 addresses and performs reverse (PTR)
lookups for IP address input. Uses only the standard library: blocking
``socket`` calls run inside the UI worker pool, wrapped with a timeout
via a thread pool.

No external dependencies, no elevated privileges required.
"""
from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import normalize_target, validate_target

_DNS_TIMEOUT = 5.0


def _resolve_with_timeout(func, argument, timeout: float):
    """Run a blocking resolver call with a hard timeout."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func, argument)
        return future.result(timeout=timeout)


class DnsLookupTool(Tool):
    name_key = "tool.dns.name"
    description_key = "tool.dns.description"
    category_key = "category.network"
    version = "1.2"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.dns.field.target.label",
            placeholder_key="tool.dns.field.target.placeholder",
        ),
        InputField(
            key="reverse",
            label_key="tool.dns.field.reverse.label",
            kind="checkbox",
            default=True,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.dns.available")

    # ------------------------------------------------------------- validation
    def validate(self, **inputs) -> list:
        return validate_target(inputs.get("target", ""))

    # ------------------------------------------------------------- execution
    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        try:
            ipaddress.ip_address(target)
        except ValueError:
            return self._run_for_hostname(target)
        return self._run_for_ip(target, bool(inputs.get("reverse", True)))

    def _run_for_hostname(self, hostname: str) -> ToolResult:
        try:
            records = _resolve_with_timeout(
                lambda host: socket.getaddrinfo(host, None), hostname, _DNS_TIMEOUT
            )
        except FutureTimeout:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                summary=tr("dns.timeout.summary"),
                error=tr("dns.timeout.detail", host=hostname, timeout=int(_DNS_TIMEOUT)),
            )
        except socket.gaierror as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("dns.resolution_failed"),
                error=tr("dns.resolution_failed_detail", host=hostname, reason=exc.strerror or exc),
            )

        ipv4 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET})
        ipv6 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET6})

        data = [(tr("dns.section.query"), [(tr("dns.host_name"), hostname)])]
        if ipv4:
            data.append((tr("dns.section.ipv4"), [(str(i + 1), value) for i, value in enumerate(ipv4)]))
        if ipv6:
            data.append((tr("dns.section.ipv6"), [(str(i + 1), value) for i, value in enumerate(ipv6)]))

        canonical = ""
        try:
            canonical = socket.getfqdn(hostname)
        except OSError:
            pass
        if canonical and canonical != hostname:
            data.append((tr("dns.section.canonical"), [(tr("dns.fqdn"), canonical)]))

        raw_lines = [f"host: {hostname}", "ipv4:"] + [f"  {ip}" for ip in ipv4]
        raw_lines += ["ipv6:"] + [f"  {ip}" for ip in ipv6]
        if canonical:
            raw_lines.append(f"fqdn: {canonical}")

        total = len(ipv4) + len(ipv6)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("dns.summary.found", count=total, host=hostname),
            data=data,
            raw_output="\n".join(raw_lines),
        )

    def _run_for_ip(self, ip: str, include_reverse: bool) -> ToolResult:
        data = [(tr("dns.section.query"), [(tr("dns.ip_address"), ip)])]
        raw_lines = [f"ip: {ip}"]

        if include_reverse:
            try:
                primary, aliases, _addresses = _resolve_with_timeout(
                    socket.gethostbyaddr, ip, _DNS_TIMEOUT
                )
                rows = [(tr("dns.host_name"), primary)]
                rows += [
                    (tr("dns.alias", index=i + 1), alias) for i, alias in enumerate(aliases)
                ]
                data.append((tr("dns.section.ptr"), rows))
                raw_lines.append(f"ptr: {primary}")
                raw_lines.extend(f"alias: {alias}" for alias in aliases)
            except FutureTimeout:
                data.append((tr("dns.section.ptr"), [(tr("dns.status"), tr("dns.ptr_timeout"))]))
                raw_lines.append("ptr: <timeout>")
            except (socket.herror, socket.gaierror, OSError):
                data.append((tr("dns.section.ptr"), [(tr("dns.status"), tr("dns.no_ptr"))]))
                raw_lines.append("ptr: <none>")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("dns.summary.ip", ip=ip),
            data=data,
            raw_output="\n".join(raw_lines),
        )
