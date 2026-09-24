"""Distribution & repository hygiene tests.

Covers: required files, documentation claims, launcher structure, installer
security properties (no iex, checksum verification, official URLs only),
no hardcoded developer paths, version consistency across packaging files.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wynes import __version__  # noqa: E402

TEXT_SUFFIXES = {".py", ".ps1", ".cmd", ".md", ".txt", ".yml", ".yaml",
                 ".gitignore"}
REQUIRED_FILES = [
    "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
    "install.ps1", "uninstall.ps1", "setup.ps1", "projectwynes.cmd",
    "packaging/projectwynes.spec", "packaging/version_info.py",
    "requirements.txt", "requirements-dev.txt",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/workflows/build-windows.yml",
]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _tracked_text_files() -> list:
    """All git-tracked text files (excludes binary assets)."""
    completed = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    )
    return [
        line.strip() for line in completed.stdout.splitlines()
        if Path(line).suffix.lower() in TEXT_SUFFIXES or "." not in Path(line).name
    ]


class TestRequiredFiles(unittest.TestCase):
    def test_all_present(self):
        for rel in REQUIRED_FILES:
            self.assertTrue((ROOT / rel).is_file(), f"missing: {rel}")


class TestNoDeveloperPaths(unittest.TestCase):
    def test_no_hardcoded_machine_paths_anywhere(self):
        offenders = []
        for rel in _tracked_text_files():
            content = _read(rel)
            if "Hakitoxx\\Desktop" in content or "Users\\Hakitoxx" in content:
                offenders.append(rel)
        self.assertEqual(offenders, [])


class TestReadmeClaims(unittest.TestCase):
    def setUp(self):
        self.readme = _read("README.md")

    def test_version_present(self):
        self.assertIn(__version__, self.readme)

    def test_command_name_is_projectwynes(self):
        self.assertGreaterEqual(self.readme.count("projectwynes"), 4)

    def test_both_methods_documented(self):
        self.assertIn("Method 1", self.readme)
        self.assertIn("Method 2", self.readme)
        self.assertIn("PowerShell", self.readme)
        self.assertIn("Download ZIP", self.readme)

    def test_installer_and_launcher_referenced(self):
        self.assertIn("install.ps1", self.readme)
        self.assertIn("setup.ps1", self.readme)
        self.assertIn("uninstall.ps1", self.readme)

    def test_no_fake_screenshot_links(self):
        # Local image references must point at docs/images (the documented
        # placeholder location); external https images (shields badges etc.)
        # are fine — they render or fail independently of the repo.
        for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", self.readme):
            target = match.group(1)
            if target.startswith(("http://", "https://")):
                continue
            self.assertTrue(target.startswith("docs/images/") or target.startswith("./docs/images/"),
                            msg=match.group(0))

    def test_version_badge_matches_package(self):
        self.assertIn(f"version-{__version__}", self.readme)


class TestLocalLauncher(unittest.TestCase):
    def test_relative_resolution_only(self):
        content = _read("projectwynes.cmd")
        self.assertIn("%~dp0", content)
        self.assertNotRegex(content, r"[A-Za-z]:\\Users\\")

    def test_points_to_same_entry_point(self):
        content = _read("projectwynes.cmd")
        self.assertIn("run.py", content)
        self.assertIn("projectwynes.exe", content)


class TestInstallerSecurity(unittest.TestCase):
    def setUp(self):
        self.installer = _read("install.ps1")

    def test_no_remote_code_execution_pattern(self):
        self.assertNotIn("iex", self.installer.lower().replace("ieq", ""))
        self.assertNotIn("Invoke-Expression", self.installer)

    def test_downloads_only_from_official_repo(self):
        urls = re.findall(r"https?://[^\s'\"`]+", self.installer)
        for url in urls:
            domain = re.sub(r"^https?://", "", url).split("/")[0]
            self.assertEqual(domain, "github.com", msg=url)
        self.assertIn("github.com/Hakitoxx/ProjectWynes", self.installer)

    def test_checksum_verification_is_mandatory(self):
        self.assertIn("Get-FileHash", self.installer)
        self.assertIn("sha256", self.installer.lower())
        # no bypass flag may exist
        self.assertNotIn("SkipChecksum", self.installer)

    def test_path_handling_is_user_scope_only(self):
        self.assertIn('"User"', self.installer)
        self.assertNotIn('"Machine"', self.installer)
        # duplicate prevention must exist
        self.assertIn("-ieq", self.installer)

    def test_install_dir_guard(self):
        self.assertIn('InstallDir -notmatch "ProjectWynes"', self.installer)


class TestPackagingConfig(unittest.TestCase):
    def test_spec_references_and_version(self):
        spec = _read("packaging/projectwynes.spec")
        self.assertIn('name="projectwynes"', spec)
        self.assertIn("console=False", spec)
        self.assertIn("run.py", spec)
        info = _read("packaging/version_info.py")
        self.assertIn(__version__, info)

    def test_powershell_scripts_parse(self):
        """Syntax-check every tracked .ps1 with the real PowerShell parser."""
        scripts = [rel for rel in _tracked_text_files() if rel.endswith(".ps1")]
        self.assertTrue(scripts, "expected installer scripts in the repo")
        for rel in scripts:
            script = ROOT / rel
            script_text = script.read_text(encoding="utf-8")
            # Windows PowerShell 5.1 reads BOM-less files as ANSI, and
            # typographic quotes in mis-decoded bytes silently corrupt string
            # parsing — so .ps1 files must stay pure ASCII.
            self.assertTrue(
                all(byte < 128 for byte in script_text.encode("utf-8")),
                msg=f"{rel}: non-ASCII characters are not allowed in .ps1 files",
            )
            code = (
                "$err=$null;"
                f"[void][System.Management.Automation.Language.Parser]::ParseFile('{script}',[ref]$null,[ref]$err);"
                "if ($err.Count) { exit 1 } else { exit 0 }"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", code],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0,
                             msg=f"{script.name}: {completed.stdout} {completed.stderr}")


if __name__ == "__main__":
    unittest.main()
