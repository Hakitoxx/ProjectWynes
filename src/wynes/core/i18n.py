"""Centralized localization (i18n) for Project Wynes.

All user-facing strings live in :mod:`wynes.locale.<lang>` modules keyed by
stable identifiers such as ``"tool.dns.name"``. Code only references keys;
language-specific ``if`` statements are not allowed in the rest of the
codebase, which keeps the code identifiers English and the strings
centralized.

The active language can be switched at runtime; listeners (e.g. the main
window) are notified so the UI can rebuild itself with the new language.
"""
from __future__ import annotations

from typing import Callable

from wynes.locale import en, tr

DEFAULT_LANGUAGE = "tr"

#: code -> (native display name, string table)
LANGUAGES: dict = {
    "tr": ("Türkçe", tr.STRINGS),
    "en": ("English", en.STRINGS),
}

_current_language: str = DEFAULT_LANGUAGE
_listeners: list = []


def available_languages() -> list:
    """Return ``[(code, native display name), ...]``."""
    return [(code, names[0]) for code, names in LANGUAGES.items()]


def get_language() -> str:
    return _current_language


def set_language(code: str) -> bool:
    """Switch the active language. Returns True if the language changed."""
    global _current_language
    if code not in LANGUAGES:
        return False
    if code == _current_language:
        return False
    _current_language = code
    for listener in list(_listeners):
        listener(code)
    return True


def add_listener(callback: Callable[[str], None]) -> None:
    """Register a ``callback(language_code)`` invoked on language change."""
    if callback not in _listeners:
        _listeners.append(callback)


def remove_listener(callback) -> None:
    if callback in _listeners:
        _listeners.remove(callback)


def tr(key: str, **params) -> str:
    """Translate ``key`` and format it with ``params``.

    Fallback order: active language -> English -> the key itself wrapped in
    markers so a missing string is visible during development instead of
    failing silently.
    """
    table = LANGUAGES[_current_language][1]
    text = table.get(key)
    if text is None:
        text = LANGUAGES["en"][1].get(key)
    if text is None:
        return f"[{key}]"
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text
