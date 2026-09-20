"""Reusable rendering of :class:`ToolResult` objects.

Every tool page shows results through :class:`ResultView`, so all tools
share the same presentation: status line, key/value sections, sortable
table sections, and a monospace raw-output area for technical detail.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wynes.core.i18n import tr
from wynes.core.tool_base import ToolResult, ToolStatus
from wynes.ui.widgets import horizontal_rule, status_dot

_MAX_TABLE_ROWS = 1000


def _status_style(status: ToolStatus) -> tuple:
    if status is ToolStatus.SUCCESS:
        return "ok", tr("state.success")
    if status is ToolStatus.TIMEOUT:
        return "warn", tr("state.timeout")
    return "error", tr("state.error")


class ResultView(QWidget):
    """Generic renderer for a :class:`ToolResult`."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(12)
        self.show_idle()

    # ------------------------------------------------------------------ API
    def show_idle(self) -> None:
        self._clear()
        label = QLabel(tr("result.empty"))
        label.setProperty("role", "muted")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._root.addStretch(1)
        self._root.addWidget(label)
        self._root.addStretch(1)

    def show_result(self, result: ToolResult) -> None:
        self._clear()

        kind, text = _status_style(result.status)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addWidget(status_dot(kind))
        status_text = QLabel(f"{tr('result.status')}: {text}")
        status_row.addWidget(status_text)
        if result.summary:
            summary = QLabel(result.summary)
            summary.setProperty("role", "muted")
            summary.setWordWrap(True)
            status_row.addWidget(summary, 1)
        self._root.addLayout(status_row)

        if result.error:
            error = QLabel(result.error)
            error.setWordWrap(True)
            error.setProperty("role", "muted")
            self._root.addWidget(error)

        for title, rows in result.data:
            self._add_section(title, rows)
        for table in result.tables:
            self._add_table(table)
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

    def _add_table(self, table) -> None:
        self._root.addWidget(horizontal_rule())
        header = QLabel(table.title)
        header.setProperty("role", "h2")
        self._root.addWidget(header)

        tree = QTreeWidget()
        tree.setColumnCount(len(table.columns))
        tree.setHeaderLabels([str(column) for column in table.columns])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setUniformRowHeights(True)
        tree.setSortingEnabled(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        rows = table.rows[:_MAX_TABLE_ROWS]
        for row in rows:
            item = QTreeWidgetItem([str(cell) for cell in row])
            tree.addTopLevelItem(item)

        for column in range(len(table.columns)):
            tree.resizeColumnToContents(column)
        if table.columns:
            tree.header().setStretchLastSection(True)

        row_height = 24
        visible = min(len(rows), 14)
        tree.setMinimumHeight(44 + row_height * max(3, visible))
        tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._root.addWidget(tree)

        if len(table.rows) > _MAX_TABLE_ROWS:
            note = QLabel(tr("result.table_truncated", shown=_MAX_TABLE_ROWS,
                             total=len(table.rows)))
            note.setProperty("role", "muted")
            self._root.addWidget(note)

    def _add_raw(self, raw: str) -> None:
        self._root.addWidget(horizontal_rule())
        header = QLabel(tr("result.raw_output"))
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
            else:
                sub = item.layout()
                if sub is not None:
                    self._delete_layout(sub)
