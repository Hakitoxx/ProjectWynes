"""Tool contract shared by every diagnostic tool in Project Wynes.

A tool is a plain Python object with no Qt dependencies, which keeps the
core layer testable and reusable. The UI builds forms from
:class:`InputField` metadata and renders :class:`ToolResult` generically.

All user-facing strings produced by tools are localized through
:func:`wynes.core.i18n.tr` at the moment they are produced. Class
attributes hold stable translation *keys*, properties resolve them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from wynes.core.i18n import tr


class ToolStatus(Enum):
    """Lifecycle status of a single tool execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class Availability(Enum):
    """Whether a tool can run in the current environment."""

    READY = "ready"
    MISSING = "missing"  # a required external dependency was not found
    UNKNOWN = "unknown"  # not checked yet


@dataclass(frozen=True)
class TableData:
    """A titled table section of a result (rendered as a sortable table)."""

    title: str
    columns: tuple
    rows: list


@dataclass(frozen=True)
class ToolResult:
    """Structured, UI-independent outcome of running a tool.

    ``data`` holds key/value sections: ``[(title, [(key, value), ...]), ...]``
    ``tables`` holds table sections; ``raw_output`` is the optional
    technical detail (shown in a monospace area).
    """

    status: ToolStatus
    summary: str = ""
    data: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    raw_output: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.SUCCESS


@dataclass(frozen=True)
class InputField:
    """Declarative description of one tool input for the generic form.

    ``kind``: ``text`` | ``checkbox`` | ``choice`` | ``file`` | ``number``
    For ``choice``, ``options`` holds ``((value, label_key), ...)``.
    For ``number``, ``minimum``/``maximum`` bound a spin box.
    """

    key: str
    label_key: str
    kind: str = "text"
    placeholder_key: str = ""
    default: object = ""
    options: tuple = ()
    minimum: int = 0
    maximum: int = 100


@dataclass(frozen=True)
class ValidationError:
    message: str
    field: Optional[str] = None


class Tool:
    """Base class for all diagnostic tools."""

    name_key: str = "tool.unnamed.name"
    description_key: str = "tool.unnamed.description"
    category_key: str = "category.other"
    version: str = ""
    input_fields: tuple = ()
    #: tools without inputs may run automatically when their page opens
    auto_run: bool = False
    #: optional informational notice shown above the form (e.g. Nmap ToU)
    notice_key: str = ""

    @property
    def name(self) -> str:
        return tr(self.name_key)

    @property
    def description(self) -> str:
        return tr(self.description_key)

    @property
    def category(self) -> str:
        return tr(self.category_key)

    def availability(self) -> tuple:
        """Return ``(Availability, localized human-readable detail)``."""
        return Availability.READY, tr("tool.builtin")

    def validate(self, **inputs) -> list:
        """Return a list of :class:`ValidationError` (empty means valid)."""
        return []

    def run(self, **inputs) -> ToolResult:
        """Execute the tool. Must be safe to call from a worker thread."""
        raise NotImplementedError
