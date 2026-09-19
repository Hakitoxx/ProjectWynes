"""Persistent application settings via QSettings.

QSettings stores values in the platform-appropriate location (Windows
registry on this machine). Only non-sensitive configuration belongs here;
secrets must never be stored.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings

_ORG = "Project Wynes"
_APP = "Wynes"


def _settings() -> QSettings:
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, _ORG, _APP)


def get_value(key: str, default=None):
    return _settings().value(key, default)


def set_value(key: str, value) -> None:
    _settings().setValue(key, value)


def save_geometry(data: QByteArray) -> None:
    set_value("ui/geometry", data)


def load_geometry() -> QByteArray | None:
    value = get_value("ui/geometry")
    return value if isinstance(value, QByteArray) and not value.isEmpty() else None
