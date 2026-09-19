"""Main window: sidebar navigation plus a stack of pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
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
from wynes.core.tool_manager import ToolManager
from wynes.ui.dashboard import DashboardPage
from wynes.ui.tool_page import ToolPage


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project Wynes")
        self.resize(1120, 720)

        self._manager = ToolManager()

        nav_panel = self._build_nav_panel()
        self._stack = QStackedWidget()
        self._build_pages()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(nav_panel)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        geometry = settings.load_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)

        self._nav.setCurrentRow(0)
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------- layout
    def _build_nav_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("navPanel")
        panel.setFixedWidth(230)
        panel.setStyleSheet("#navPanel { background-color: #1e2023; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 18, 0, 12)
        layout.setSpacing(0)

        brand = QLabel("WYNES")
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

    def _build_pages(self) -> None:
        entries = self._manager.all_entries()
        self._row_to_page: dict = {}

        self._add_nav_item("Dashboard")
        self._row_to_page[self._nav.count() - 1] = self._stack.count()
        self._stack.addWidget(DashboardPage(self._manager))

        current_category = None
        for entry in entries:
            if entry.tool.category != current_category:
                current_category = entry.tool.category
                self._add_nav_item(current_category.upper(), selectable=False)
            self._add_nav_item(entry.tool.name, indent=True)
            self._row_to_page[self._nav.count() - 1] = self._stack.count()
            self._stack.addWidget(ToolPage(entry))

    def _add_nav_item(self, text: str, *, selectable: bool = True, indent: bool = False) -> None:
        item = QListWidgetItem(("    " + text) if indent else text)
        if not selectable:
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
        self._nav.addItem(item)

    def _on_nav_changed(self, row: int) -> None:
        # Category header rows are not in the mapping and have no page.
        page = self._row_to_page.get(row)
        if page is not None:
            self._stack.setCurrentIndex(page)

    # ------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:
        settings.save_geometry(self.saveGeometry())
        super().closeEvent(event)
