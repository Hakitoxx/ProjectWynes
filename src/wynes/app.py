"""Application bootstrap: QApplication, localization, first launch."""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from wynes import __version__
from wynes.core import settings
from wynes.core.i18n import DEFAULT_LANGUAGE, set_language
from wynes.ui.settings_page import LANGUAGE_SETTING_KEY
from wynes.ui.theme import APP_QSS


def _init_language(smoke_test: bool, lang_override: str) -> None:
    """Set the active language; ask on first launch (never in smoke test)."""
    chosen = lang_override or str(settings.get_value(LANGUAGE_SETTING_KEY, "") or "")
    if chosen:
        set_language(chosen)
        return
    set_language(DEFAULT_LANGUAGE)
    if smoke_test:
        return
    from wynes.ui.first_launch import FirstLaunchDialog

    dialog = FirstLaunchDialog()
    dialog.exec()
    settings.set_value(LANGUAGE_SETTING_KEY, dialog.selected)
    set_language(dialog.selected)


def run(smoke_test: bool = False, lang: str = "") -> int:
    """Start the application.

    With ``smoke_test=True`` the main window is created (in the chosen or
    default language, without the first-launch dialog) and the function
    returns immediately without entering the event loop.
    ``lang`` forces a language code for one run without persisting it.
    """
    QApplication.setOrganizationName("Project Wynes")
    QApplication.setApplicationName("Wynes")
    QApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv[:1])
    _init_language(smoke_test, lang)
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
