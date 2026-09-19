"""Application bootstrap: QApplication setup and main window startup."""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from wynes import __version__
from wynes.ui.theme import APP_QSS


def run(smoke_test: bool = False) -> int:
    """Start the application.

    With ``smoke_test=True`` the main window is created and the function
    returns immediately without entering the event loop. Used by automated
    verification together with the ``offscreen`` Qt platform.
    """
    QApplication.setOrganizationName("Project Wynes")
    QApplication.setApplicationName("Wynes")
    QApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    font = app.font()
    font.setPointSize(10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(APP_QSS)

    from wynes.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    if smoke_test:
        app.processEvents()
        window.close()
        return 0
    return app.exec()
