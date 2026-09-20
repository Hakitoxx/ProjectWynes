"""Dashboard: the start page of Project Wynes.

Shows what the application is, its version, quick access to the most
common diagnostics, the availability state of every tool and a compact
local system summary.
"""
from __future__ import annotations

import platform
import shutil
import socket

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import Qt, qVersion
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wynes import __version__
from wynes.core.i18n import tr
from wynes.core.tool_base import Availability
from wynes.core.tool_manager import ToolManager
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label, status_dot

_QUICK_ACCESS_CLASSES = ("DnsLookupTool", "PingTool", "PortCheckTool",
                         "HttpHeadersTool", "NmapScanTool")


def _kv_grid(rows) -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(28)
    grid.setVerticalSpacing(6)
    for row, (key, value) in enumerate(rows):
        key_label = QLabel(key)
        key_label.setProperty("role", "muted")
        key_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        value_label = QLabel(value)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_label.setWordWrap(True)
        grid.addWidget(key_label, row, 0)
        grid.addWidget(value_label, row, 1)
    grid.setColumnStretch(1, 1)
    return grid


class DashboardPage(QWidget):
    def __init__(self, manager: ToolManager, open_page, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # header: name + version chip
        header_row = QHBoxLayout()
        header_row.addWidget(header_label("Project Wynes"))
        version = QLabel(__version__)
        version.setProperty("chip", True)
        header_row.addWidget(version, 0, Qt.AlignmentFlag.AlignVCenter)
        header_row.addStretch(1)
        root.addLayout(header_row)
        root.addWidget(muted_label(tr("dashboard.subtitle")))
        root.addWidget(horizontal_rule())

        root.addWidget(self._quick_access_card(manager, open_page))

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._tools_card(manager), 3)
        columns.addWidget(self._system_card(), 2)
        root.addLayout(columns, 1)

    # ---------------------------------------------------------------- cards
    def _quick_access_card(self, manager: ToolManager, open_page) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)
        title = QLabel(tr("dashboard.quick_access"))
        title.setProperty("role", "h2")
        layout.addWidget(title)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        known = {type(entry.tool).__name__: entry.tool for entry in manager.all_entries()}
        for class_name in _QUICK_ACCESS_CLASSES:
            tool = known.get(class_name)
            if tool is None:
                continue
            button = QPushButton(tool.name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, name=class_name: open_page(f"tool:{name}")
            )
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _tools_card(self, manager: ToolManager) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel(tr("dashboard.tools_title"))
        title.setProperty("role", "h2")
        layout.addWidget(title)

        for entry in manager.all_entries():
            row = QHBoxLayout()
            row.setSpacing(8)
            if entry.availability is Availability.READY:
                row.addWidget(status_dot("ok"))
            elif entry.availability is Availability.MISSING:
                row.addWidget(status_dot("error"))
            else:
                row.addWidget(status_dot("planned"))

            name = QLabel(entry.tool.name)
            row.addWidget(name)
            detail = QLabel(entry.detail)
            detail.setProperty("role", "muted")
            detail.setWordWrap(False)
            row.addWidget(detail, 1)
            layout.addLayout(row)

        layout.addStretch(1)
        return box

    def _system_card(self) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel(tr("dashboard.system_title"))
        title.setProperty("role", "h2")
        layout.addWidget(title)

        nmap_path = shutil.which("nmap")
        nmap_text = nmap_path if nmap_path else tr("dashboard.nmap_missing")

        layout.addLayout(
            _kv_grid(
                [
                    (tr("sysinfo.hostname"), socket.gethostname()),
                    (tr("sysinfo.os"), f"{platform.system()} {platform.release()}"),
                    (tr("sysinfo.python"), platform.python_version()),
                    ("Qt / PySide", f"{qVersion()} / {PYSIDE_VERSION}"),
                    (tr("dashboard.nmap_path"), nmap_text),
                    (tr("sysinfo.wynes_version"), __version__),
                ]
            )
        )
        layout.addStretch(1)

        note = muted_label(tr("dashboard.privacy_note"))
        layout.addWidget(note)
        return box
