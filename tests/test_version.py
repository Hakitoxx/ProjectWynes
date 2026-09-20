"""Version consistency test: 1.2.0 must be the version everywhere."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


class TestVersion(unittest.TestCase):
    EXPECTED = "1.2.0"

    def test_package_version(self):
        from wynes import __version__

        self.assertEqual(__version__, self.EXPECTED)

    def test_readme_mentions_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(self.EXPECTED, readme)

    def test_no_leftover_placeholder_version(self):
        from wynes import __version__

        self.assertNotEqual(__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
