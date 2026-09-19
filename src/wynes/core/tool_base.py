"""Tool contract shared by every diagnostic tool in Project Wynes.

A tool is a plain Python object with no Qt dependencies, which keeps the
core layer testable and reusable. The UI layer builds its forms from
:class:`InputField` metadata and renders :class:`ToolResult` generically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
class ToolResult:
    """Structured, UI-independent outcome of running a tool.

    ``data`` holds the rendered sections shown in the GUI:
    ``[(section title, [(key, value), ...]), ...]``.
    """

    status: ToolStatus
    summary: str = ""
    data: list = field(default_factory=list)
    raw_output: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.SUCCESS


@dataclass(frozen=True)
class InputField:
    """Declarative description of one tool input for the generic form."""

    key: str
    label: str
    kind: str = "text"  # "text" or "checkbox"
    placeholder: str = ""
    default: object = ""


@dataclass(frozen=True)
class ValidationError:
    message: str
    field: Optional[str] = None


class Tool:
    """Base class for all diagnostic tools."""

    name: str = "Unnamed Tool"
    description: str = ""
    category: str = "General"
    version: str = ""
    #: Tools that work offline (used for planned/placeholder tools).
    offline: bool = True
    input_fields: tuple = ()

    def availability(self) -> tuple:
        """Return ``(Availability, human-readable detail)``."""
        return Availability.READY, "Built-in"

    def validate(self, **inputs) -> list:
        """Return a list of :class:`ValidationError` (empty means valid)."""
        return []

    def run(self, **inputs) -> ToolResult:
        """Execute the tool. Must be safe to call from a worker thread."""
        raise NotImplementedError
