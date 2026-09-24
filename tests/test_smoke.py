"""End-to-end smoke tests: build the whole GUI headless in both languages."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestSmokeBothLanguages(unittest.TestCase):
    def _run_smoke(self, lang: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        last = None
        for _attempt in range(2):  # headless startup on a busy runner can stall
            try:
                return subprocess.run(
                    [sys.executable, str(ROOT / "run.py"), "--smoke-test", "--lang", lang],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
            except subprocess.TimeoutExpired as exc:
                last = exc
        raise last

    def test_turkish(self):
        completed = self._run_smoke("tr")
        self.assertEqual(completed.returncode, 0,
                         msg=completed.stdout + "\n" + completed.stderr)

    def test_english(self):
        completed = self._run_smoke("en")
        self.assertEqual(completed.returncode, 0,
                         msg=completed.stdout + "\n" + completed.stderr)


class TestGuiConstruction(unittest.TestCase):
    """Direct in-process GUI construction checks (offscreen platform)."""

    _app = None

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        sys.path.insert(0, str(ROOT / "src"))
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_main_window_contains_all_pages(self):
        from wynes.ui.main_window import MainWindow

        window = MainWindow()
        try:
            tokens = set(window._token_to_page)
            self.assertIn("dashboard", tokens)
            self.assertIn("settings", tokens)
            self.assertIn("about", tokens)
            tool_tokens = [t for t in tokens if t.startswith("tool:")]
            self.assertEqual(len(tool_tokens), 11)
        finally:
            window.close()
            window.deleteLater()

    def test_first_launch_dialog_defaults(self):
        from wynes.core import i18n
        from wynes.ui.first_launch import FirstLaunchDialog

        dialog = FirstLaunchDialog()
        self.assertEqual(dialog.selected, i18n.DEFAULT_LANGUAGE)
        dialog._choose("en")
        self.assertEqual(dialog.selected, "en")
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
