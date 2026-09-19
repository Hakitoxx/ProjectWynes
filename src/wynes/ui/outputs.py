"""Reusable rendering of :class:`ToolResult` objects.

Every tool page shows results through :class:`ResultView`, so all tools
share the same presentation: status line, optional structured sections,
and collapsible raw output.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from wynes.core.tool_base import ToolResult, ToolStatus
from wynes.ui.widgets import horizontal_rule


def _section_status(status: ToolStatus) -> tuple:
    if status is ToolStatus.SUCCESS:
        return ("ok", "Completed successfully")
    if status is ToolStatus.TIMEOUT:
        return ("error", "Timed out")
    return ("error", "Failed")


class ResultView(QWidget):
    """Generic renderer for a :class:`ToolResult`."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(12)
        self.show_idle("Enter the input and press Run.")

    # ------------------------------------------------------------------ API
    def show_idle(self, message: str) -> None:
        self._clear()
        label = QLabel(message)
        label.setProperty("role", "muted")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._root.addStretch(1)
        self._root.addWidget(label)
        self._root.addStretch(1)

    def show_result(self, result: ToolResult) -> None:
        self._clear()

        kind, text = _section_status(result.status)
        status_label = QLabel(f"Status: {text}")
        status_label.setProperty("dot", kind)
        self._root.addWidget(status_label)

        if result.summary:
            summary = QLabel(result.summary)
            summary.setWordWrap(True)
            self._root.addWidget(summary)
        if result.error:
            error = QLabel(result.error)
            error.setWordWrap(True)
            error.setProperty("role", "muted")
            self._root.addWidget(error)

        for title, rows in result.data:
            self._add_section(title, rows)

        if result.raw_output:
            self._add_raw(result.raw_output)

        self._root.addStretch(1)

    # -------------------------------------------------------------- helpers
    def _add_section(self, title: str, rows) -> None:
        if not rows:
            return
        self._root.addWidget(horizontal_rule())
        header = QLabel(title)
        header.setProperty("role", "h2")
        self._root.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(4)
        for row, (key, value) in enumerate(rows):
            key_label = QLabel(str(key))
            key_label.setProperty("role", "muted")
            key_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            value_label = QLabel(str(value))
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value_label.setWordWrap(True)
            grid.addWidget(key_label, row, 0)
            grid.addWidget(value_label, row, 1)
        grid.setColumnStretch(1, 1)
        self._root.addLayout(grid)

    def _add_raw(self, raw: str) -> None:
        self._root.addWidget(horizontal_rule())
        header = QLabel("Raw Output")
        header.setProperty("role", "h2")
        self._root.addWidget(header)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(raw)
        text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        text.setMinimumHeight(110)
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._root.addWidget(text)

    def _clear(self) -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                layout = item.layout()
                if layout is not None:
                    self._delete_layout(layout)

    def _delete_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
