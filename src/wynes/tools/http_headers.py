"""HTTP response header inspection.

Sends a single ``HEAD`` request (falling back to ``GET``-without-body for
servers that reject HEAD) using the standard-library ``http.client``.
No response body is downloaded, executed or stored. Redirects are
reported, not followed automatically.
"""
from __future__ import annotations

import http.client
import socket
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    TableData,
    Tool,
    ToolResult,
    ToolStatus,
)
from wynes.core.validators import validate_url

_TIMEOUT = 10.0
_USER_AGENT = "Wynes/1.2.0 (+https://github.com/Hakitoxx/ProjectWynes)"
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_HEAD_FALLBACK_STATUSES = {400, 403, 405, 501}


@dataclass
class HttpResponse:
    url: str
    method: str
    status: int = 0
    reason: str = ""
    headers: list = field(default_factory=list)
    elapsed_ms: float = 0.0

    def header(self, name: str) -> str:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return ""


def _request(url: str, method: str, timeout: float) -> HttpResponse:
    parts = urlsplit(url if "://" in url else f"https://{url}")
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query

    connection_cls = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_cls(host, port, timeout=timeout)
    started = time.perf_counter()
    try:
        connection.request(method, path, headers={"User-Agent": _USER_AGENT})
        response = connection.getresponse()
        headers = list(response.getheaders())
        elapsed = (time.perf_counter() - started) * 1000
        return HttpResponse(
            url=parts.geturl(), method=method, status=response.status,
            reason=response.reason, headers=headers, elapsed_ms=elapsed,
        )
    finally:
        connection.close()  # body is never read -> nothing is downloaded


class HttpHeadersTool(Tool):
    name_key = "tool.http.name"
    description_key = "tool.http.description"
    category_key = "category.network"
    version = "1.0"
    input_fields = (
        InputField(
            key="url",
            label_key="tool.http.field.url.label",
            placeholder_key="tool.http.field.url.placeholder",
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.http.available")

    def validate(self, **inputs) -> list:
        return validate_url(inputs.get("url", ""))

    def run(self, **inputs) -> ToolResult:
        url = str(inputs.get("url", "")).strip()
        try:
            result = _request(url, "HEAD", _TIMEOUT)
            if result.status in _HEAD_FALLBACK_STATUSES:
                result = _request(url, "GET", _TIMEOUT)
        except (socket.timeout, TimeoutError):
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                summary=tr("http.timeout_summary"),
                error=tr("http.timeout_detail", url=url, timeout=int(_TIMEOUT)),
            )
        except ssl.SSLCertVerificationError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("http.cert_error"),
                error=tr("http.cert_error_detail", url=url, reason=exc.verify_message or exc),
            )
        except ssl.SSLError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("http.tls_error"),
                error=tr("http.tls_error_detail", reason=str(exc.reason or exc)[:200]),
            )
        except socket.gaierror:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("http.dns_error"),
                error=tr("http.dns_error_detail", url=url),
            )
        except (ConnectionRefusedError, ConnectionResetError) as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("http.connection_failed"),
                error=tr("http.connection_failed_detail", reason=str(exc)[:200]),
            )
        except (http.client.HTTPException, OSError) as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("state.error"),
                error=str(exc)[:300],
            )

        return self._render(result)

    # -------------------------------------------------------------- rendering
    def _render(self, result: HttpResponse) -> ToolResult:
        data = [(
            tr("http.section.response"),
            [
                (tr("http.url"), result.url),
                (tr("http.method"), result.method),
                (tr("http.status"), f"{result.status} {result.reason}".strip()),
                (tr("http.elapsed"), tr("fmt.ms", value=round(result.elapsed_ms, 1))),
            ],
        )]
        summary_rows = data[0][1]
        server = result.header("Server")
        if server:
            summary_rows.append((tr("http.server"), server))
        content_type = result.header("Content-Type")
        if content_type:
            summary_rows.append((tr("http.content_type"), content_type))

        location = result.header("Location")
        if result.status in _REDIRECT_STATUSES and location:
            data.append((tr("http.section.redirect"), [(tr("http.redirect_to"), location)]))

        tables = [TableData(
            title=tr("http.section.headers", count=len(result.headers)),
            columns=(tr("http.col.header"), tr("http.col.value")),
            rows=[(name, value) for name, value in result.headers],
        )]

        raw_lines = [f"{result.method} {result.url}",
                     f"HTTP {result.status} {result.reason}".strip()]
        raw_lines += [f"{name}: {value}" for name, value in result.headers]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("http.summary", status=result.status, url=result.url),
            data=data,
            tables=tables,
            raw_output="\n".join(raw_lines),
        )
