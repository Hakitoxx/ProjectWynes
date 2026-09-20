"""Local file hashing.

Computes a digest of a local file with chunked streaming reads (1 MiB
blocks) so even large files never need to fit into memory. The file never
leaves the machine and no copies are created.
"""
from __future__ import annotations

import hashlib
import os
import time

from wynes.core.i18n import tr
from wynes.core.tool_base import (
    Availability,
    InputField,
    Tool,
    ToolResult,
    ToolStatus,
    ValidationError,
)
from wynes.core.validators import validate_file_path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB
ALGORITHMS = ("sha256", "sha512", "sha1", "md5")


def format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num_bytes} B"


def hash_file(path: str, algorithm: str) -> tuple:
    """Return ``(hexdigest, size, elapsed_seconds)`` for ``path``."""
    digest = hashlib.new(algorithm)
    size = os.path.getsize(path)
    started = time.perf_counter()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest(), size, time.perf_counter() - started


class FileHashTool(Tool):
    name_key = "tool.hash.name"
    description_key = "tool.hash.description"
    category_key = "category.files"
    version = "1.0"
    input_fields = (
        InputField(key="path", label_key="tool.hash.field.path.label", kind="file"),
        InputField(
            key="algorithm",
            label_key="tool.hash.field.algorithm.label",
            kind="choice",
            default="sha256",
            options=tuple((name, f"hash.algo.{name}") for name in ALGORITHMS),
        ),
    )

    def availability(self) -> tuple:
        return Availability.READY, tr("tool.hash.available")

    def validate(self, **inputs) -> list:
        errors = validate_file_path(inputs.get("path", ""))
        algorithm = inputs.get("algorithm", "sha256")
        if algorithm not in ALGORITHMS:
            errors.append(ValidationError(tr("hash.error.unknown_algorithm"), field="algorithm"))
        return errors

    def run(self, **inputs) -> ToolResult:
        path = str(inputs.get("path", "")).strip()
        algorithm = str(inputs.get("algorithm", "sha256"))
        try:
            if algorithm not in hashlib.algorithms_available:
                raise ValueError(algorithm)
            hexdigest, size, elapsed = hash_file(path, algorithm)
        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("hash.error.permission"),
                error=tr("hash.error.permission_detail", path=path),
            )
        except (ValueError, TypeError):
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("hash.error.unknown_algorithm"),
                error=tr("hash.error.unknown_algorithm_detail", algorithm=algorithm),
            )
        except OSError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                summary=tr("hash.error.read_failed"),
                error=str(exc)[:200],
            )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            summary=tr("hash.summary", algorithm=algorithm.upper(),
                       name=os.path.basename(path)),
            data=[(tr("hash.section.file"), [
                (tr("hash.file_name"), os.path.basename(path)),
                (tr("hash.file_path"), os.path.abspath(path)),
                (tr("hash.file_size"), f"{format_size(size)} ({size} {tr('unit.bytes')})"),
                (tr("hash.algorithm"), algorithm.upper()),
                (tr("hash.elapsed"), tr("fmt.seconds", value=round(elapsed, 2))),
            ]), (tr("hash.section.digest"), [
                (algorithm.upper(), hexdigest),
            ])],
            raw_output=f"{algorithm.upper()}  {hexdigest}\n{os.path.abspath(path)}\n",
        )
