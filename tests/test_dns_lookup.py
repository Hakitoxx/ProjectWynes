"""Core tests for the DNS lookup tool and the tool infrastructure.

Run from the project root:

    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.process import guard_exceptions  # noqa: E402
from wynes.core.tool_base import ToolResult, ToolStatus  # noqa: E402
from wynes.core.tool_manager import ToolManager  # noqa: E402
from wynes.tools.dns_lookup import DnsLookupTool  # noqa: E402


class TestDnsValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = DnsLookupTool()

    def test_empty_input_is_rejected(self):
        errors = self.tool.validate(target="   ")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, "target")

    def test_valid_hostname_is_accepted(self):
        self.assertEqual(self.tool.validate(target="example.com"), [])

    def test_valid_ipv4_is_accepted(self):
        self.assertEqual(self.tool.validate(target="192.0.2.1"), [])

    def test_valid_ipv6_is_accepted(self):
        self.assertEqual(self.tool.validate(target="2001:db8::1"), [])

    def test_illegal_characters_are_rejected(self):
        errors = self.tool.validate(target="bad host; rm -rf /")
        self.assertTrue(errors)

    def test_too_long_input_is_rejected(self):
        errors = self.tool.validate(target="a" * 300)
        self.assertTrue(errors)


class TestDnsExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = DnsLookupTool()

    def test_localhost_resolves(self):
        result = self.tool.run(target="localhost", reverse=False)
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        flattened = str(result.data)
        self.assertTrue("127.0.0.1" in flattened or "::1" in flattened)

    def test_ipv4_input_succeeds(self):
        result = self.tool.run(target="127.0.0.1", reverse=False)
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)

    def test_unresolvable_name_reports_error_not_crash(self):
        result = self.tool.run(target="nonexistent.invalid", reverse=False)
        self.assertIn(result.status, (ToolStatus.ERROR, ToolStatus.TIMEOUT))
        self.assertFalse(result.ok)
        self.assertTrue(result.error)


class TestInfrastructure(unittest.TestCase):
    def test_guard_exceptions_converts_failures(self):
        def boom(**_kwargs):
            raise RuntimeError("boom")

        result = guard_exceptions(boom)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("boom", result.error)

    def test_guard_exceptions_passes_results_through(self):
        expected = ToolResult(status=ToolStatus.SUCCESS, summary="fine")
        result = guard_exceptions(lambda **_kw: expected)
        self.assertIs(result, expected)

    def test_manager_lists_tools_with_status(self):
        manager = ToolManager()
        entries = manager.all_entries()
        self.assertGreaterEqual(len(entries), 1)
        for entry in entries:
            self.assertIsNotNone(entry.availability)
            self.assertTrue(entry.tool.name)

    def test_manager_blocks_planned_tools(self):
        manager = ToolManager()
        planned = [e for e in manager.all_entries() if e.planned]
        self.assertTrue(planned, "expected at least one planned tool entry")
        for entry in planned:
            self.assertIsNotNone(manager.ensure_ready(entry.tool))


if __name__ == "__main__":
    unittest.main()
