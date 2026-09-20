"""Main window: sidebar navigation plus a rebuildable page stack.

Pages are identified by stable tokens (``dashboard``, ``tool:<Class>``,
``settings``, ``about``) so the UI can be rebuilt in place when the
language changes without losing the user's current location.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from wynes import __version__
from wynes.core import settings
from wynes.core.i18n import add_listener, tr
from wynes.core.tool_manager import ToolManager
from wynes.ui.about_page import AboutPage
from wynes.ui.dashboard import DashboardPage
from wynes.ui.settings_page import SettingsPage
from wynes.ui.tool_page import ToolPage

_CATEGORY_ORDER = ("category.network", "category.system", "category.files")
_LAST_PAGE_SETTING = "ui/last_page"


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Project Wynes {__version__}")
        self.setMinimumSize(1000, 640)
        self.resize(1120, 720)

        self._manager = ToolManager()
        self._row_to_token: dict = {}
        self._token_to_row: dict = {}
        self._token_to_page: dict = {}

        nav_panel = self._build_nav_panel()
        self._stack = QStackedWidget()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(nav_panel)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self.rebuild_ui(keep_token=str(settings.get_value(_LAST_PAGE_SETTING, "dashboard")))

        geometry = settings.load_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)

        self.statusBar().showMessage(tr("state.ready"))
        add_listener(self._on_language_changed)

    # ------------------------------------------------------------- layout
    def _build_nav_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("navPanel")
        panel.setFixedWidth(230)
        panel.setStyleSheet("#navPanel { background-color: #1e2023; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 18, 0, 12)
        layout.setSpacing(0)

        brand = QLabel("PROJECT WYNES")
        brand.setProperty("role", "h1")
        brand.setContentsMargins(20, 0, 0, 2)
        layout.addWidget(brand)
        version = QLabel(f"v{__version__}")
        version.setProperty("role", "muted")
        version.setContentsMargins(20, 0, 0, 14)
        layout.addWidget(version)

        self._nav = QListWidget()
        self._nav.setObjectName("nav")
        self._nav.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self._nav, 1)
        return panel

    # -------------------------------------------------------------- rebuild
    def rebuild_ui(self, keep_token: str = "dashboard") -> None:
        """(Re)build navigation and pages — used at startup and on language
        changes, so every label re-renders in the active language."""
        self._manager.clear_cache()
        self._row_to_token.clear()
        self._token_to_row.clear()
        self._token_to_page.clear()

        while self._stack.count():
            widget = self._stack.widget(0)
            self._stack.removeWidget(widget)
            widget.deleteLater()

        self._nav.blockSignals(True)
        self._nav.clear()

        self._add_page("dashboard", tr("nav.dashboard"),
                       DashboardPage(self._manager, self.open_page))

        current_category = None
        for entry in self._manager.all_entries():
            tool = entry.tool
            if tool.category_key != current_category:
                current_category = tool.category_key
                self._add_nav_header(tr(tool.category_key))
            self._add_page(f"tool:{type(tool).__name__}", tool.name,
                           ToolPage(entry, self._manager), indent=True)

        self._add_nav_separator()
        self._add_page("settings", tr("nav.settings"), SettingsPage(self._manager))
        self._add_page("about", tr("nav.about"), AboutPage())

        self._nav.blockSignals(False)
        row = self._token_to_row.get(keep_token, self._token_to_row["dashboard"])
        self._nav.setCurrentRow(row)
        self.statusBar().showMessage(tr("state.ready"))

    def open_page(self, token: str) -> None:
        row = self._token_to_row.get(token)
        if row is not None:
            self._nav.setCurrentRow(row)

    # --------------------------------------------------------------- helpers
    def _add_page(self, token: str, title: str, widget: QWidget, indent: bool = False) -> None:
        item = QListWidgetItem(("    " + title) if indent else title)
        self._nav.addItem(item)
        row = self._nav.count() - 1
        self._row_to_token[row] = token
        self._token_to_row[token] = row
        self._token_to_page[token] = self._stack.count()
        self._stack.addWidget(widget)

    def _add_nav_header(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(Qt.GlobalColor.gray)
        self._nav.addItem(item)

    def _add_nav_separator(self) -> None:
        item = QListWidgetItem(" ")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self._nav.addItem(item)

    def _on_nav_changed(self, row: int) -> None:
        token = self._row_to_token.get(row)
        if token is None:
            return
        self._stack.setCurrentIndex(self._token_to_page[token])
        settings.set_value(_LAST_PAGE_SETTING, token)

    def _on_language_changed(self, _code: str) -> None:
        # defer: the Settings combo lives inside the page being rebuilt
        current_token = self._row_to_token.get(self._nav.currentRow(), "dashboard")
        QTimer.singleShot(0, lambda: self.rebuild_ui(keep_token=current_token))

    # ------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:
        settings.save_geometry(self.saveGeometry())
        super().closeEvent(event)
