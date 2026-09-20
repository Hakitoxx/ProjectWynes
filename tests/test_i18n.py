"""Localization tests: key parity, fallbacks, formatting, coverage.

A regex pass over the source tree guarantees every literal ``tr("key")``
in the codebase exists in BOTH language tables, so a missing translation
can never reach the UI unnoticed.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wynes.core import i18n  # noqa: E402
from wynes.locale import en, tr as tr_module  # noqa: E402

_TR_CALL_RE = re.compile(r"""tr\(\s*"([a-z0-9_]+(?:\.[a-z0-9_]+)+)"\s*[,)]""")


def _all_source_keys() -> set:
    keys = set()
    for path in (ROOT / "src").rglob("*.py"):
        if "locale" in path.parts:
            continue
        keys.update(_TR_CALL_RE.findall(path.read_text(encoding="utf-8")))
    return keys


class TestLocaleParity(unittest.TestCase):
    def test_key_sets_are_identical(self):
        en_keys = set(en.STRINGS)
        tr_keys = set(tr_module.STRINGS)
        self.assertEqual(en_keys, tr_keys,
                         msg=f"en-only: {sorted(en_keys - tr_keys)} | "
                             f"tr-only: {sorted(tr_keys - en_keys)}")

    def test_all_code_keys_exist_in_both_languages(self):
        keys = _all_source_keys()
        self.assertTrue(keys, "expected to find tr() calls in the source")
        for name, table in (("en", en.STRINGS), ("tr", tr_module.STRINGS)):
            missing = sorted(key for key in keys if key not in table)
            self.assertFalse(missing, f"{name} is missing keys: {missing}")

    def test_no_empty_strings(self):
        for name, table in (("en", en.STRINGS), ("tr", tr_module.STRINGS)):
            empty = [key for key, value in table.items()
                     if not str(value).strip() and "description" not in key]
            self.assertFalse(empty, f"{name} has empty values: {empty}")


class TestI18nRuntime(unittest.TestCase):
    def setUp(self):
        self._previous = i18n.get_language()

    def tearDown(self):
        i18n.set_language(self._previous)

    def test_default_language_is_turkish(self):
        self.assertEqual(i18n.DEFAULT_LANGUAGE, "tr")

    def test_translate_known_key_both_languages(self):
        i18n.set_language("tr")
        self.assertEqual(i18n.tr("action.run"), "Çalıştır")
        i18n.set_language("en")
        self.assertEqual(i18n.tr("action.run"), "Run")

    def test_parameter_formatting(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("port.open_summary", target="x", port=80),
                         "Port 80 is open on x")

    def test_unknown_key_falls_back_visibly(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("does.not.exist"), "[does.not.exist]")

    def test_unknown_language_is_ignored(self):
        before = i18n.get_language()
        self.assertFalse(i18n.set_language("xx"))
        self.assertEqual(i18n.get_language(), before)

    def test_listeners_are_notified(self):
        seen = []
        i18n.add_listener(seen.append)
        try:
            i18n.set_language("en")
            i18n.set_language("tr")
        finally:
            i18n.remove_listener(seen.append)
        self.assertEqual(seen, ["en", "tr"])

    def test_set_same_language_notifies_nobody(self):
        seen = []
        i18n.add_listener(seen.append)
        try:
            current = i18n.get_language()
            i18n.set_language(current)
        finally:
            i18n.remove_listener(seen.append)
        self.assertEqual(seen, [])

    def test_dynamic_option_keys_exist(self):
        # choice options are built dynamically (e.g. f"hash.algo.{name}");
        # ensure every one of them exists in both languages
        from wynes.tools.file_hash import ALGORITHMS
        from wynes.tools.nmap_scan import SCAN_PROFILES

        for name, table in (("en", en.STRINGS), ("tr", tr_module.STRINGS)):
            for algo in ALGORITHMS:
                self.assertIn(f"hash.algo.{algo}", table, f"{name}")
            for profile in SCAN_PROFILES:
                self.assertIn(f"nmap.profile.{profile}", table, f"{name}")


if __name__ == "__main__":
    unittest.main()
