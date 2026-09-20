"""About page: version, technology, purpose and usage scope."""
from __future__ import annotations

import platform

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import Qt, qVersion
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from wynes import __version__
from wynes.core.i18n import tr
from wynes.ui.widgets import card, header_label, horizontal_rule, muted_label

REPOSITORY_URL = "https://github.com/Hakitoxx/ProjectWynes"


class AboutPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.addWidget(header_label(tr("about.title")))
        version = QLabel(__version__)
        version.setProperty("chip", True)
        header_row.addWidget(version, 0, Qt.AlignmentFlag.AlignVCenter)
        header_row.addStretch(1)
        root.addLayout(header_row)
        root.addWidget(horizontal_rule())

        # --- description
        desc_card = card()
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setContentsMargins(18, 16, 18, 16)
        desc_layout.setSpacing(8)
        desc = QLabel(tr("about.description"))
        desc.setWordWrap(True)
        desc_layout.addWidget(desc)
        root.addWidget(desc_card)

        # --- technology
        tech_card = card()
        tech_layout = QVBoxLayout(tech_card)
        tech_layout.setContentsMargins(18, 16, 18, 16)
        tech_layout.setSpacing(6)
        tech_title = QLabel(tr("about.technology"))
        tech_title.setProperty("role", "h2")
        tech_layout.addWidget(tech_title)
        for line in (
            f"Python {platform.python_version()}",
            f"PySide6 {PYSIDE_VERSION} (Qt {qVersion()})",
            f"{platform.system()} {platform.release()} / {platform.machine()}",
        ):
            tech_layout.addWidget(muted_label(line, wrap=False))
        root.addWidget(tech_card)

        # --- repository
        repo_card = card()
        repo_layout = QVBoxLayout(repo_card)
        repo_layout.setContentsMargins(18, 16, 18, 16)
        repo_title = QLabel(tr("about.repository"))
        repo_title.setProperty("role", "h2")
        repo_layout.addWidget(repo_title)
        link = QLabel(f'<a href="{REPOSITORY_URL}" style="color:#c8c9cb;">{REPOSITORY_URL}</a>')
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        repo_layout.addWidget(link)
        root.addWidget(repo_card)

        # --- scope
        scope_card = card()
        scope_layout = QVBoxLayout(scope_card)
        scope_layout.setContentsMargins(18, 16, 18, 16)
        scope_layout.setSpacing(8)
        scope_title = QLabel(tr("about.scope_title"))
        scope_title.setProperty("role", "h2")
        scope_layout.addWidget(scope_title)
        scope_text = QLabel(tr("about.scope_text"))
        scope_text.setWordWrap(True)
        scope_text.setProperty("role", "muted")
        scope_layout.addWidget(scope_text)
        root.addWidget(scope_card)

        root.addStretch(1)
