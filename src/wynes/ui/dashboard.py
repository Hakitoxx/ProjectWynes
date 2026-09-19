"""Dashboard: the start page of Project Wynes.

Shows the state of the application at a glance — registered diagnostic
tools with their availability, plus basic local system information.
Deliberately simple; no charts, no gimmicks.
"""
from __future__ import annotations

import platform
import shutil
import socket

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import Qt, qVersion
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from wynes import __version__
from wynes.core.tool_base import Availability
from wynes.core.tool_manager import ToolManager
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label, status_dot


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
    def __init__(self, manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(header_label("Dashboard"))
        root.addWidget(
            muted_label(
                "Minimalist toolkit for defensive network and system diagnostics. "
                "Select a tool in the sidebar."
            )
        )
        root.addWidget(horizontal_rule())

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._tools_card(manager), 3)
        columns.addWidget(self._system_card(), 2)
        root.addLayout(columns, 1)

    # ---------------------------------------------------------------- cards
    def _tools_card(self, manager: ToolManager) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel("Diagnostic Tools")
        title.setProperty("role", "h2")
        layout.addWidget(title)

        for entry in manager.all_entries():
            row = QHBoxLayout()
            row.setSpacing(8)
            if entry.planned or entry.availability is Availability.UNKNOWN:
                row.addWidget(status_dot("planned"))
            elif entry.availability is Availability.READY:
                row.addWidget(status_dot("ok"))
            else:
                row.addWidget(status_dot("error"))

            name = QLabel(entry.tool.name)
            row.addWidget(name)
            detail = QLabel(entry.detail)
            detail.setProperty("role", "muted")
            row.addWidget(detail)
            row.addStretch(1)
            layout.addLayout(row)

        layout.addStretch(1)
        return box

    def _system_card(self) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel("System Information")
        title.setProperty("role", "h2")
        layout.addWidget(title)

        nmap_path = shutil.which("nmap")
        nmap_text = nmap_path if nmap_path else "Not found (Nmap scan tool will be unavailable)"

        layout.addLayout(
            _kv_grid(
                [
                    ("Host name", socket.gethostname()),
                    ("Operating system", f"{platform.system()} {platform.release()} ({platform.machine()})"),
                    ("Python", platform.python_version()),
                    ("Qt / PySide", f"{qVersion()} / {PYSIDE_VERSION}"),
                    ("Nmap on PATH", nmap_text),
                    ("Wynes version", __version__),
                ]
            )
        )
        layout.addStretch(1)
        return box
