"""First-launch language selection dialog.

Shown once, when no language preference exists yet. Because no language
is chosen yet, descriptive text is intentionally shown in both supported
languages; the choice buttons use plain text (no emoji flags).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from wynes import __version__
from wynes.core.i18n import DEFAULT_LANGUAGE
from wynes.ui.widgets import horizontal_rule


class FirstLaunchDialog(QDialog):
    """Modal dialog returning the chosen language code via ``selected``."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.selected: str = DEFAULT_LANGUAGE
        self.setWindowTitle("Project Wynes")
        self.setModal(True)
        self.setFixedSize(520, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(12)

        brand = QLabel("PROJECT WYNES")
        brand.setProperty("role", "h1")
        layout.addWidget(brand)
        version = QLabel(f"v{__version__}")
        version.setProperty("role", "muted")
        layout.addWidget(version)
        layout.addWidget(horizontal_rule())

        desc_tr = QLabel(
            "Ağ ve sistem tanılamaları için minimalist bir masaüstü araç seti. "
            "Devam etmeden önce arayüz dilini seçin."
        )
        desc_tr.setWordWrap(True)
        layout.addWidget(desc_tr)

        desc_en = QLabel(
            "A minimalist desktop toolkit for network and system diagnostics. "
            "Please choose your interface language to continue."
        )
        desc_en.setWordWrap(True)
        desc_en.setProperty("role", "muted")
        layout.addWidget(desc_en)

        layout.addStretch(1)

        title = QLabel("Dil seçin / Choose language")
        title.setProperty("role", "h2")
        layout.addWidget(title)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        for code, display in (("tr", "Türkçe"), ("en", "English")):
            button = QPushButton(display)
            button.setProperty("primary", True)
            button.setMinimumHeight(44)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, lang=code: self._choose(lang))
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def _choose(self, code: str) -> None:
        self.selected = code
        self.accept()
