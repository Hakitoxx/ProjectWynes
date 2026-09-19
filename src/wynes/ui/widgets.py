"""Small reusable UI building blocks shared by all pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel


def header_label(text: str, *, role: str = "h1") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    return label


def muted_label(text: str, *, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "muted")
    label.setWordWrap(wrap)
    return label


def status_dot(kind: str) -> QLabel:
    """Small colored dot: ``ok`` (ready), ``planned`` or ``error``."""
    dot = QLabel("●")
    dot.setProperty("dot", kind)
    dot.setFixedWidth(14)
    dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return dot


def horizontal_rule() -> QFrame:
    rule = QFrame()
    rule.setProperty("rule", True)
    rule.setFrameShape(QFrame.Shape.NoFrame)
    return rule


def card() -> QFrame:
    frame = QFrame()
    frame.setProperty("card", True)
    return frame
