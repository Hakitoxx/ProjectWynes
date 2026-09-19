"""DNS lookup tool.

Resolves host names to IPv4/IPv6 addresses and performs reverse (PTR)
lookups for IP address input. Implemented with the Python standard
library (blocking ``socket`` calls) executed inside the UI worker pool.

No external dependencies, no elevated privileges required.
"""
from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from wynes.core.tool_base import (
    Availability,
    InputField,
    Tool,
    ToolResult,
    ToolStatus,
    ValidationError,
)

_DNS_TIMEOUT = 5.0
_HOSTNAME_MAX_LENGTH = 253


class DnsLookupTool(Tool):
    name = "DNS Lookup"
    description = "Resolve host names to IP addresses and perform reverse (PTR) lookups."
    category = "Network"
    version = "1.0"
    input_fields = (
        InputField(
            key="target",
            label="Host name or IP address",
            placeholder="example.com  or  93.184.216.34",
        ),
        InputField(
            key="reverse",
            label="Include reverse lookup (PTR) for IP addresses",
            kind="checkbox",
            default=True,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, "Built-in (Python standard library)"

    # ------------------------------------------------------------- validation
    def validate(self, **inputs) -> list:
        target = str(inputs.get("target", "")).strip()
        if not target:
            return [ValidationError("Enter a host name or IP address.", field="target")]
        if len(target) > _HOSTNAME_MAX_LENGTH:
            return [ValidationError("Input is too long (maximum 253 characters).", field="target")]
        try:
            ipaddress.ip_address(target)
            return []  # valid IP address
        except ValueError:
            pass
        allowed = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        if any(char not in allowed for char in target):
            return [
                ValidationError(
                    "Host names may only contain letters, digits, dots and hyphens.",
                    field="target",
                )
            ]
        return []

    # ------------------------------------------------------------- execution
    def run(self, **inputs) -> ToolResult:
        target = str(inputs.get("target", "")).strip()
        try:
            addresses = ipaddress.ip_address(target)
        except ValueError:
            addresses = None

        if addresses is not None:
            return self._run_for_ip(target, bool(inputs.get("reverse", True)))
        return self._run_for_hostname(target)

    def _run_for_hostname(self, hostname: str) -> ToolResult:
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(socket.getaddrinfo, hostname, None)
                records = future.result(timeout=_DNS_TIMEOUT)
        except FutureTimeout:
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                summary="DNS resolution timed out",
                error=f'No answer within {int(_DNS_TIMEOUT)} seconds for "{hostname}".',
            )
        except socket.gaierror as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary="Name resolution failed",
                error=f'"{hostname}" could not be resolved: {exc.strerror or exc}',
            )

        ipv4 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET})
        ipv6 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET6})

        data = [("Query", [("Host name", hostname)])]
        if ipv4:
            data.append(("IPv4 Addresses (A)", [(str(i + 1), value) for i, value in enumerate(ipv4)]))
        if ipv6:
            data.append(("IPv6 Addresses (AAAA)", [(str(i + 1), value) for i, value in enumerate(ipv6)]))

        canonical = ""
        try:
            canonical = socket.getfqdn(hostname)
        except OSError:
            pass
        if canonical and canonical != hostname:
            data.append(("Canonical Name", [("FQDN", canonical)]))

        raw_lines = [f"host: {hostname}", "ipv4:"] + [f"  {ip}" for ip in ipv4]
        raw_lines += ["ipv6:"] + [f"  {ip}" for ip in ipv6]
        if canonical:
            raw_lines.append(f"fqdn: {canonical}")

        total = len(ipv4) + len(ipv6)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=f"{total} address(es) found for {hostname}",
            data=data,
            raw_output="\n".join(raw_lines),
        )

    def _run_for_ip(self, ip: str, include_reverse: bool) -> ToolResult:
        data = [("Query", [("IP address", ip)])]
        raw_lines = [f"ip: {ip}"]

        if include_reverse:
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(socket.gethostbyaddr, ip)
                    primary, aliases, _addresses = future.result(timeout=_DNS_TIMEOUT)
                data.append(
                    ("Reverse Lookup (PTR)", [("Host name", primary)] + [
                        (f"Alias {i + 1}", alias) for i, alias in enumerate(aliases)
                    ])
                )
                raw_lines.append(f"ptr: {primary}")
                raw_lines.extend(f"alias: {alias}" for alias in aliases)
            except FutureTimeout:
                data.append(("Reverse Lookup (PTR)", [("Status", "Timed out")]))
                raw_lines.append("ptr: <timeout>")
            except (socket.herror, socket.gaierror, OSError):
                data.append(("Reverse Lookup (PTR)", [("Status", "No PTR record found")]))
                raw_lines.append("ptr: <none>")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=f"Processed IP address {ip}",
            data=data,
            raw_output="\n".join(raw_lines),
        )
