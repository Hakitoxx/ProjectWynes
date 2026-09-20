"""Settings page: application language and Nmap executable path.

Everything applies immediately and persists via QSettings. Language
changes notify the main window, which rebuilds the UI in place.
"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wynes.core import settings
from wynes.core.i18n import available_languages, get_language, set_language, tr
from wynes.core.tool_manager import ToolManager
from wynes.tools.nmap_scan import find_nmap_executable
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label

LANGUAGE_SETTING_KEY = "app/language"
NMAP_PATH_KEY = "nmap/path"


class SettingsPage(QWidget):
    def __init__(self, manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self._manager = manager

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        root.addWidget(header_label(tr("settings.title")))
        root.addWidget(muted_label(tr("settings.subtitle")))
        root.addWidget(horizontal_rule())
        root.addWidget(self._language_card())
        root.addWidget(self._nmap_card())
        root.addStretch(1)

    # ---------------------------------------------------------------- cards
    def _language_card(self) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel(tr("settings.language.title"))
        title.setProperty("role", "h2")
        layout.addWidget(title)

        row = QHBoxLayout()
        label = QLabel(tr("settings.language.label"))
        label.setProperty("role", "muted")
        row.addWidget(label)

        combo = QComboBox()
        for code, display in available_languages():
            combo.addItem(display, userData=code)
        index = combo.findData(get_language())
        combo.setCurrentIndex(max(0, index))
        combo.setFixedWidth(180)
        combo.currentIndexChanged.connect(
            lambda _index, c=combo: self._change_language(c.currentData())
        )
        row.addWidget(combo)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(muted_label(tr("settings.language.note")))
        return box

    def _nmap_card(self) -> QWidget:
        box = card()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel(tr("settings.nmap.title"))
        title.setProperty("role", "h2")
        layout.addWidget(title)

        detected = find_nmap_executable()
        effective = detected or tr("settings.nmap.not_found")
        layout.addWidget(muted_label(tr("settings.nmap.effective", path=effective)))

        row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(tr("settings.nmap.path_placeholder"))
        configured = str(settings.get_value(NMAP_PATH_KEY, "") or "")
        self._path_edit.setText(configured)
        row.addWidget(self._path_edit, 1)
        layout.addLayout(row)

        buttons = QHBoxLayout()
        save = QPushButton(tr("action.save"))
        save.setProperty("primary", True)
        save.clicked.connect(self._save_nmap_path)
        buttons.addWidget(save)
        browse = QPushButton(tr("action.browse"))
        browse.clicked.connect(self._browse_nmap)
        buttons.addWidget(browse)
        reset = QPushButton(tr("action.use_auto"))
        reset.clicked.connect(self._reset_nmap_path)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._nmap_status = muted_label("")
        layout.addWidget(self._nmap_status)
        layout.addWidget(muted_label(tr("settings.nmap.note")))
        return box

    # ---------------------------------------------------------------- logic
    def _change_language(self, code: str) -> None:
        if code and code != get_language():
            settings.set_value(LANGUAGE_SETTING_KEY, code)
            set_language(code)  # notifies listeners -> UI rebuilds

    def _save_nmap_path(self) -> None:
        path = self._path_edit.text().strip()
        if path and not os.path.isfile(path):
            self._nmap_status.setText(tr("settings.nmap.invalid"))
            return
        settings.set_value(NMAP_PATH_KEY, path)
        self._manager.clear_cache()
        self._nmap_status.setText(tr("settings.saved"))

    def _reset_nmap_path(self) -> None:
        self._path_edit.setText("")
        settings.set_value(NMAP_PATH_KEY, "")
        self._manager.clear_cache()
        self._nmap_status.setText(tr("settings.saved"))

    def _browse_nmap(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _selected = QFileDialog.getOpenFileName(
            self, tr("settings.nmap.title"), "", "nmap.exe (nmap.exe);;*"
        )
        if path:
            self._path_edit.setText(path)
