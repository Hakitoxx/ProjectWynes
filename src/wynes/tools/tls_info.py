"""TLS / certificate inspection.

Opens a real TLS connection (standard library ``ssl``) and reports the
negotiated protocol, cipher and certificate details. When certificate
verification fails, the certificate is fetched again without verification
so the user can inspect *why* it is untrusted — the failed verification
status is always shown prominently.
"""
from __future__ import annotations

import os
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import (
    is_ip_address,
    normalize_target,
    validate_port,
    validate_target,
)


@dataclass
class TlsReport:
    host: str
    port: int
    verified: bool = False
    verify_message: str = ""
    protocol: str = ""
    cipher: str = ""
    cipher_bits: object = ""
    subject: str = ""
    issuer: str = ""
    serial: str = ""
    not_before: str = ""
    not_after: str = ""
    days_remaining: object = ""
    san_entries: list = None

    def __post_init__(self) -> None:
        if self.san_entries is None:
            self.san_entries = []


def _flatten_name(name_items) -> str:
    """Turn getpeercert() subject/issuer tuples into "CN=x, O=y" text."""
    parts = []
    for rdn in name_items or ():
        for key, value in rdn:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _format_time(raw: str) -> tuple:
    """Convert 'Sep 20 12:00:00 2026 GMT' -> (display, datetime)."""
    seconds = ssl.cert_time_to_seconds(raw)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%d %H:%M UTC"), moment


def fetch_certificate(host: str, port: int, timeout: float) -> TlsReport:
    """Open a verified TLS connection; on verification failure retry
    unverified (clearly flagged) to still surface certificate details."""
    report = TlsReport(host=host, port=port)
    is_ip = is_ip_address(host)

    context = ssl.create_default_context()
    if is_ip:
        # IP targets have no DNS host name to check against the certificate
        context.check_hostname = False

    try:
        with socket.create_connection((host, port), timeout=timeout) as tcp:
            server_name = None if is_ip else host
            with context.wrap_socket(tcp, server_hostname=server_name) as tls:
                report.verified = True
                _fill_from_socket(report, tls)
                return report
    except ssl.SSLCertVerificationError as exc:
        report.verified = False
        report.verify_message = exc.verify_message or str(exc)

    # Verification failed: fetch the certificate anyway (unverified) so the
    # user can see why it failed. The failed status stays visible.
    insecure = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    insecure.check_hostname = False
    insecure.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=timeout) as tcp:
        with insecure.wrap_socket(tcp) as tls:
            _fill_from_socket(report, tls)
    return report


def _decode_der_certificate(binary: bytes) -> dict:
    """Decode a DER certificate into the familiar getpeercert() dict shape.

    Uses the (long-standing) ``_ssl._test_decode_cert`` helper on a
    temporary PEM file; returns {} if unavailable so callers degrade
    gracefully.
    """
    import tempfile

    try:
        decode = getattr(ssl._ssl, "_test_decode_cert", None)
        if decode is None or not binary:
            return {}
        pem = ssl.DER_cert_to_PEM_cert(binary)
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False,
                                         encoding="ascii") as handle:
            handle.write(pem)
            temp_path = handle.name
        try:
            return decode(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    except Exception:
        return {}


def _fill_from_socket(report: TlsReport, tls) -> None:
    report.protocol = tls.version() or ""
    cipher = tls.cipher()
    if cipher:
        report.cipher = cipher[0]
        report.cipher_bits = cipher[2]
    cert = tls.getpeercert(binary_form=False)
    if not cert:
        # With verification disabled, CPython returns an empty dict;
        # decode the DER form so invalid certificates are still inspectable.
        cert = _decode_der_certificate(tls.getpeercert(binary_form=True) or b"")
    if not cert:
        return
    report.subject = _flatten_name(cert.get("subject"))
    report.issuer = _flatten_name(cert.get("issuer"))
    report.serial = cert.get("serialNumber", "")
    if cert.get("notBefore"):
        display, _ = _format_time(cert["notBefore"])
        report.not_before = display
    if cert.get("notAfter"):
        display, moment = _format_time(cert["notAfter"])
        report.not_after = display
        report.days_remaining = (moment - datetime.now(timezone.utc)).days
    sans = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"]
    report.san_entries = sans[:8]


class TlsInfoTool(Tool):
    name_key = "tool.tls.name"
    description_key = "tool.tls.description"
    category_key = "category.network"
    version = "1.0"
    input_fields = (
        InputField(
            key="target",
            label_key="tool.tls.field.target.label",
            placeholder_key="tool.tls.field.target.placeholder",
        ),
        InputField(
            key="port",
            label_key="tool.tls.field.port.label",
            kind="number",
            default=443,
            minimum=1,
            maximum=65535,
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.tls.available")

    def validate(self, **inputs) -> list:
        errors = validate_target(inputs.get("target", ""))
        errors += validate_port(inputs.get("port", ""))
        return errors

    def run(self, **inputs) -> ToolResult:
        target = normalize_target(inputs.get("target", ""))
        port = int(inputs.get("port", 443))
        timeout = 10.0
        try:
            report = fetch_certificate(target, port, timeout)
        except (socket.timeout, TimeoutError):
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                summary=tr("tls.timeout_summary"),
                error=tr("tls.timeout_detail", host=target, port=port, timeout=int(timeout)),
            )
        except socket.gaierror:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("tls.dns_error"),
                error=tr("tls.dns_error_detail", host=target),
            )
        except (ConnectionRefusedError, ConnectionResetError) as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("tls.connection_failed"),
                error=tr("tls.connection_failed_detail", host=target, port=port, reason=str(exc)[:150]),
            )
        except ssl.SSLError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("tls.handshake_failed"),
                error=tr("tls.handshake_failed_detail", host=target, port=port,
                         reason=str(exc.reason or exc)[:200]),
            )

        return self._render(report)

    # -------------------------------------------------------------- rendering
    def _render(self, report: TlsReport) -> ToolResult:
        connection_rows = [
            (tr("tls.host"), f"{report.host}:{report.port}"),
            (tr("tls.verification"),
             tr("tls.verified") if report.verified else tr("tls.not_verified")),
        ]
        if not report.verified and report.verify_message:
            connection_rows.append((tr("tls.verify_error"), report.verify_message))
        if report.protocol:
            connection_rows.append((tr("tls.protocol"), report.protocol))
        if report.cipher:
            cipher = f"{report.cipher} ({report.cipher_bits} bit)" if report.cipher_bits else report.cipher
            connection_rows.append((tr("tls.cipher"), cipher))

        data = [(tr("tls.section.connection"), connection_rows)]

        if report.subject or report.issuer:
            cert_rows = []
            if report.subject:
                cert_rows.append((tr("tls.subject"), report.subject))
            if report.issuer:
                cert_rows.append((tr("tls.issuer"), report.issuer))
            if report.serial:
                cert_rows.append((tr("tls.serial"), report.serial))
            if report.not_before:
                cert_rows.append((tr("tls.valid_from"), report.not_before))
            if report.not_after:
                cert_rows.append((tr("tls.valid_until"), report.not_after))
            if report.days_remaining != "":
                cert_rows.append((tr("tls.days_remaining"), str(report.days_remaining)))
            data.append((tr("tls.section.certificate"), cert_rows))
        if report.san_entries:
            data.append((tr("tls.section.san"), [(str(i + 1), name) for i, name in
                                                 enumerate(report.san_entries)]))

        ok = report.verified
        return ToolResult(
            status=ToolStatus.SUCCESS if ok else ToolStatus.ERROR,
            summary=(tr("tls.summary_ok", host=report.host)
                     if ok else tr("tls.summary_unverified", host=report.host)),
            data=data,
        )
