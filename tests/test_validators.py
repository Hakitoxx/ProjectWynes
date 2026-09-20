"""Shared validator tests (localization-independent behavior)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core import validators  # noqa: E402


class TestTargetValidation(unittest.TestCase):
    def test_valid_inputs(self):
        for value in ("example.com", "127.0.0.1", "::1", "sub.domain-example.org"):
            self.assertEqual(validators.validate_target(value), [], msg=value)

    def test_rejects_empty_and_long(self):
        self.assertTrue(validators.validate_target(""))
        self.assertTrue(validators.validate_target("x" * 300))

    def test_rejects_option_injection(self):
        for value in ("-e", "--script=vuln", "-oN out.txt", "/etc/passwd"):
            self.assertTrue(validators.validate_target(value), msg=value)

    def test_rejects_shell_metacharacters(self):
        for value in ("host; rm -rf", "a|b", "a&b", "$(whoami)", "`id`"):
            self.assertTrue(validators.validate_target(value), msg=value)

    def test_cidr_only_when_allowed(self):
        self.assertTrue(validators.validate_target("192.168.1.0/24"))
        self.assertEqual(
            validators.validate_target("192.168.1.0/24", allow_cidr=True,
                                       min_cidr_prefix=24),
            [],
        )

    def test_nmap_rejects_broad_cidr(self):
        self.assertTrue(validators.sanitize_nmap_target("10.0.0.0/8"))
        self.assertTrue(validators.sanitize_nmap_target("192.168.0.0/16"))
        self.assertEqual(validators.sanitize_nmap_target("192.168.1.0/24"), [])
        self.assertEqual(validators.sanitize_nmap_target("192.168.1.10"), [])


class TestPortValidation(unittest.TestCase):
    def test_valid(self):
        for value in ("1", "443", "65535", 8080):
            self.assertEqual(validators.validate_port(value), [], msg=value)

    def test_invalid(self):
        for value in ("0", "65536", "-1", "abc", "", None):
            self.assertTrue(validators.validate_port(value), msg=value)


class TestUrlValidation(unittest.TestCase):
    def test_valid(self):
        for value in ("https://example.com", "http://192.168.1.1:8080/x?y=1",
                      "example.com/path"):
            self.assertEqual(validators.validate_url(value), [], msg=value)

    def test_invalid(self):
        for value in ("", "ftp://example.com", "http://", "javascript:alert(1)",
                      "https://bad host/", "http://example.com:99999/"):
            self.assertTrue(validators.validate_url(value), msg=value)


class TestFileValidation(unittest.TestCase):
    def test_existing_readable_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"data")
            path = handle.name
        try:
            self.assertEqual(validators.validate_file_path(path), [])
        finally:
            os.unlink(path)

    def test_missing_and_directory(self):
        self.assertTrue(validators.validate_file_path(""))
        self.assertTrue(validators.validate_file_path("C:\\definitely\\missing.x"))
        self.assertTrue(validators.validate_file_path(tempfile.gettempdir()))


if __name__ == "__main__":
    unittest.main()
