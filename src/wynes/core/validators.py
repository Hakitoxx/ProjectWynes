"""Shared input validators for network targets, URLs, ports and files.

Validators return a list of :class:`ValidationError` with *localized*
messages (resolved at validation time). An empty list means valid input.
"""
from __future__ import annotations

import ipaddress
import os
import re
from urllib.parse import urlsplit

from wynes.core.i18n import tr
from wynes.core.tool_base import ValidationError

MAX_HOSTNAME_LENGTH = 253
_HOSTNAME_ALLOWED = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
)


def is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def is_valid_hostname(value: str) -> bool:
    if not value or len(value) > MAX_HOSTNAME_LENGTH:
        return False
    return all(char in _HOSTNAME_ALLOWED for char in value)


def is_valid_cidr(value: str, min_prefix: int = 0) -> bool:
    """True for CIDR notation such as ``192.168.1.0/24``.

    ``min_prefix`` limits the network size (e.g. 24 rejects anything
    broader than a /24) to keep diagnostics away from mass scanning.
    """
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return network.prefixlen >= min_prefix


def validate_target(value: str, field: str = "target", *, allow_cidr: bool = False,
                    min_cidr_prefix: int = 0) -> list:
    """Validate a host name, IP address, or (optionally) a small CIDR range."""
    target = (value or "").strip()
    if not target:
        return [ValidationError(tr("validation.target_required"), field=field)]
    if len(target) > MAX_HOSTNAME_LENGTH:
        return [ValidationError(tr("validation.too_long", max=MAX_HOSTNAME_LENGTH), field=field)]
    # RFC 952/1123: names may not start with a hyphen. This also prevents
    # option injection when the target is passed as a CLI argument.
    if target.startswith(("-", "/")):
        return [ValidationError(tr("validation.target_invalid"), field=field)]
    if is_ip_address(target) or is_valid_hostname(target):
        return []
    if allow_cidr and "/" in target:
        if is_valid_cidr(target, min_prefix=min_cidr_prefix):
            return []
        return [ValidationError(tr("validation.cidr_invalid"), field=field)]
    return [ValidationError(tr("validation.target_invalid"), field=field)]


def validate_port(value, field: str = "port") -> list:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return [ValidationError(tr("validation.port_invalid"), field=field)]
    if not 1 <= port <= 65535:
        return [ValidationError(tr("validation.port_invalid"), field=field)]
    return []


def validate_url(value: str, field: str = "url") -> list:
    text = (value or "").strip()
    if not text:
        return [ValidationError(tr("validation.url_required"), field=field)]
    candidate = text if "://" in text else f"https://{text}"
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return [ValidationError(tr("validation.url_invalid"), field=field)]
    if parts.scheme not in ("http", "https"):
        return [ValidationError(tr("validation.url_scheme"), field=field)]
    host = parts.hostname or ""
    if not (is_valid_hostname(host) or is_ip_address(host)):
        return [ValidationError(tr("validation.url_host_invalid"), field=field)]
    try:
        _ = parts.port  # raises ValueError for out-of-range ports
    except ValueError:
        return [ValidationError(tr("validation.port_invalid"), field=field)]
    return []


def validate_file_path(value: str, field: str = "path") -> list:
    path = (value or "").strip()
    if not path:
        return [ValidationError(tr("validation.file_required"), field=field)]
    if not os.path.exists(path):
        return [ValidationError(tr("validation.file_missing"), field=field)]
    if not os.path.isfile(path):
        return [ValidationError(tr("validation.not_a_file"), field=field)]
    if not os.access(path, os.R_OK):
        return [ValidationError(tr("validation.file_unreadable"), field=field)]
    return []


def sanitize_nmap_target(value: str, field: str = "target") -> list:
    """Nmap targets: single host/IP or a small CIDR range (max /24).

    Deliberately rejects broad ranges: Wynes is a diagnostic tool, not a
    mass-scanning tool.
    """
    return validate_target(value, field=field, allow_cidr=True, min_cidr_prefix=24)


def normalize_target(value: str) -> str:
    """Strip whitespace (kept as a function so all tools normalize alike)."""
    return (value or "").strip()


def safe_filename_component(value: str) -> str:
    """Reduce a string to characters safe for display-only file names."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)[:200]
