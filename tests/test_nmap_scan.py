"""Nmap integration tests.

Parsing and validation run everywhere. Detection and the loopback host
discovery run only when Nmap is actually installed — the suite never
requires Nmap.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import Availability, ToolStatus  # noqa: E402
from wynes.tools.nmap_scan import (  # noqa: E402
    SCAN_PROFILES,
    NmapScanTool,
    find_nmap_executable,
    nmap_version,
    parse_nmap_output,
)

SAMPLE = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-09-20 18:30
Nmap scan report for 192.168.1.1
Host is up (0.0010s latency).
Not shown: 97 closed tcp ports (conn-refused)
PORT     STATE SERVICE
53/tcp   open  domain
80/tcp   open  http
443/tcp  open  https

Nmap scan report for 192.168.1.20
Host seems down.

Nmap done: 256 IP addresses (1 host up) scanned in 3.21 seconds
"""


class TestNmapParsing(unittest.TestCase):
    def test_parse_hosts_and_ports(self):
        hosts = parse_nmap_output(SAMPLE)
        self.assertEqual(len(hosts), 2)

        up_host = hosts[0]
        self.assertTrue(up_host.up)
        self.assertEqual(up_host.host, "192.168.1.1")
        self.assertEqual(up_host.ports, [
            ("53/tcp", "open", "domain"),
            ("80/tcp", "open", "http"),
            ("443/tcp", "open", "https"),
        ])

        self.assertFalse(hosts[1].up)
        self.assertEqual(hosts[1].ports, [])

    def test_empty_output(self):
        self.assertEqual(parse_nmap_output(""), [])


class TestNmapValidation(unittest.TestCase):
    def setUp(self):
        self.tool = NmapScanTool()

    def test_accepts_single_host_and_small_cidr(self):
        self.assertEqual(self.tool.validate(target="192.168.1.1", profile="quick"), [])
        self.assertEqual(self.tool.validate(target="192.168.1.0/24", profile="quick"), [])

    def test_rejects_broad_ranges_and_garbage(self):
        self.assertTrue(self.tool.validate(target="10.0.0.0/8"))
        self.assertTrue(self.tool.validate(target="192.168.0.0/16"))
        self.assertTrue(self.tool.validate(target="-sS 1.2.3.4"))
        self.assertTrue(self.tool.validate(target="1.2.3.4 --script=vuln"))

    def test_rejects_unknown_profile(self):
        self.assertTrue(self.tool.validate(target="127.0.0.1", profile="nse-vuln"))

    def test_profiles_contain_no_offensive_flags(self):
        forbidden = {"--script", "-O", "-A", "-sS", "-sU", "-Pn", "-T4", "-T5"}
        for name, args in SCAN_PROFILES.items():
            for flag in forbidden:
                self.assertNotIn(flag, args, msg=f"{name}: {flag}")
            self.assertLessEqual(len(args), 7)


class TestNmapDetection(unittest.TestCase):
    def test_detection_never_crashes(self):
        path = find_nmap_executable()
        self.assertIsInstance(path, str)
        if path:
            version = nmap_version(path)
            self.assertTrue(version)

    def test_availability_both_states(self):
        tool = NmapScanTool()
        availability, detail = tool.availability()
        self.assertIn(availability, (Availability.READY, Availability.MISSING))
        self.assertTrue(detail)


@unittest.skipUnless(find_nmap_executable(), "Nmap not installed on this machine")
class TestNmapLoopbackRun(unittest.TestCase):
    def test_discover_loopback(self):
        tool = NmapScanTool()
        result = tool.run(target="127.0.0.1", profile="discover")
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertTrue(result.raw_output)
        self.assertIn("127.0.0.1", result.raw_output)


if __name__ == "__main__":
    unittest.main()
