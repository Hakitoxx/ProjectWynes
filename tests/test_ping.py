"""Ping tool tests: argument construction and locale-proof parsing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.ping import PingTool, build_ping_args, parse_ping_output  # noqa: E402

EN_SAMPLE = """
Pinging example.com [93.184.216.34] with 32 bytes of data:
Reply from 93.184.216.34: bytes=32 time=21ms TTL=52
Reply from 93.184.216.34: bytes=32 time<1ms TTL=52
Reply from 93.184.216.34: bytes=32 time=22ms TTL=52
Reply from 93.184.216.34: bytes=32 time=20ms TTL=52

Ping statistics for 93.184.216.34:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 20ms, Maximum = 22ms, Average = 21ms
"""

# Turkish Windows output for the same command (structure-only differences)
TR_SAMPLE = """
93.184.216.34 için Ping Denemesi 32 bayt veri ile:
93.184.216.34 yanıtı: bayt=32 süre=4ms TTL=52
93.184.216.34 yanıtı: bayt=32 süre<1ms TTL=52
93.184.216.34 yanıtı: bayt=32 süre=5ms TTL=52
93.184.216.34 yanıtı: bayt=32 süre=3ms TTL=52
"""

FAIL_SAMPLE = """
Ping request could not find host nope.invalid. Please check the name and try again.
"""


class TestPingArgs(unittest.TestCase):
    def test_windows_args_contain_no_shell_and_safe_order(self):
        args = build_ping_args("8.8.8.8", 4, 1000)
        self.assertIsInstance(args, list)
        self.assertEqual(args[0], "ping")
        self.assertEqual(args[-1], "8.8.8.8")
        if sys.platform.startswith("win"):
            self.assertEqual(args, ["ping", "-n", "4", "-w", "1000", "8.8.8.8"])
        else:
            self.assertIn("-c", args)

    def test_target_is_single_argument(self):
        args = build_ping_args("example.com", 2, 500)
        self.assertEqual(len([a for a in args if a == "example.com"]), 1)


class TestPingParsing(unittest.TestCase):
    def test_english_output(self):
        stats = parse_ping_output(EN_SAMPLE, 4)
        self.assertEqual(stats.replies, 4)
        self.assertEqual(stats.resolved_ip, "93.184.216.34")
        self.assertEqual(min(stats.times_ms), 1)  # "time<1ms" -> 1 ms
        self.assertEqual(max(stats.times_ms), 22)

    def test_turkish_output_parses_identically(self):
        stats = parse_ping_output(TR_SAMPLE, 4)
        self.assertEqual(stats.replies, 4)
        self.assertEqual(len(stats.times_ms), 4)
        self.assertIn(3, stats.times_ms)

    def test_failure_has_no_replies(self):
        stats = parse_ping_output(FAIL_SAMPLE, 4)
        self.assertEqual(stats.replies, 0)


class TestPingToolLocal(unittest.TestCase):
    """Loopback integration: 127.0.0.1 must be pingable on every OS."""

    def setUp(self):
        self.tool = PingTool()

    def test_validation(self):
        self.assertTrue(self.tool.validate(target=""))
        self.assertTrue(self.tool.validate(target="-n"))
        self.assertEqual(self.tool.validate(target="127.0.0.1"), [])

    def test_loopback_ping(self):
        result = self.tool.run(target="127.0.0.1", count=2)
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertTrue(result.raw_output)

    def test_unresolvable_host_reports_failure_not_crash(self):
        result = self.tool.run(target="nonexistent.invalid", count=2)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertTrue(result.summary)


if __name__ == "__main__":
    unittest.main()
