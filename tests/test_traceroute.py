"""Traceroute tests: argument building and structural output parsing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.tools.traceroute import (  # noqa: E402
    build_traceroute_args,
    parse_traceroute_output,
)

EN_SAMPLE = """
Tracing route to example.com [93.184.216.34]
over a maximum of 30 hops:

  1    <1 ms    <1 ms    <1 ms  192.168.1.1
  2     4 ms     3 ms     4 ms  host.isp.example [203.0.113.1]
  3     *        *        *     Request timed out.
  4    21 ms    20 ms    22 ms  93.184.216.34

Trace complete.
"""

TR_SAMPLE = """
93.184.216.34 hedefi üzerinden en fazla 30 durakla izleme:

  1   <1 ms    <1 ms    <1 ms  192.168.1.1
  2    5 ms     4 ms     4 ms  93.184.216.34

İzleme tamamlandı.
"""


class TestTracerouteArgs(unittest.TestCase):
    def test_windows_args(self):
        args = build_traceroute_args("example.com", 20, 1000, resolve_names=False)
        if sys.platform.startswith("win"):
            self.assertEqual(args, ["tracert", "-h", "20", "-w", "1000", "-d",
                                    "example.com"])
        else:
            self.assertEqual(args[0], "traceroute")
        self.assertEqual(args[-1], "example.com")

    def test_resolve_flag_controls_d_flag(self):
        with_resolve = build_traceroute_args("x.example", 5, 500, resolve_names=True)
        without = build_traceroute_args("x.example", 5, 500, resolve_names=False)
        if sys.platform.startswith("win"):
            self.assertNotIn("-d", with_resolve)
            self.assertIn("-d", without)


class TestTracerouteParsing(unittest.TestCase):
    def test_english(self):
        hops = parse_traceroute_output(EN_SAMPLE)
        self.assertEqual(len(hops), 4)

        self.assertEqual(hops[0].number, 1)
        self.assertEqual(hops[0].ip, "192.168.1.1")
        self.assertEqual(hops[0].times_ms, [1, 1, 1])

        self.assertEqual(hops[1].host, "host.isp.example")
        self.assertEqual(hops[1].ip, "203.0.113.1")
        self.assertEqual(hops[1].times_ms, [4, 3, 4])

        self.assertEqual(hops[2].missed, 3)
        self.assertEqual(hops[2].times_ms, [])
        self.assertEqual(hops[2].ip, "")

        self.assertEqual(hops[3].ip, "93.184.216.34")

    def test_turkish_output_parses_identically(self):
        hops = parse_traceroute_output(TR_SAMPLE)
        self.assertEqual(len(hops), 2)
        self.assertEqual(hops[0].ip, "192.168.1.1")
        self.assertEqual(hops[1].times_ms, [5, 4, 4])

    def test_empty_output(self):
        self.assertEqual(parse_traceroute_output(""), [])


if __name__ == "__main__":
    unittest.main()
