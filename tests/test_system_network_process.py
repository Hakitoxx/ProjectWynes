"""System Information, Network Information and Process List tests.

All three query the local machine only; assertions focus on structural
correctness (works, has content, no crashes) rather than exact values.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes import __version__  # noqa: E402
from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.network_info import NetworkInfoTool  # noqa: E402
from wynes.tools.process_list import ProcessListTool  # noqa: E402
from wynes.tools.system_info import SystemInfoTool  # noqa: E402


class TestSystemInfo(unittest.TestCase):
    def test_collects_core_facts(self):
        result = SystemInfoTool().run()
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        flattened = str(result.data)
        self.assertIn(__version__, flattened)
        self.assertEqual(len(result.data), 3)  # OS + hardware + runtime sections


class TestNetworkInfo(unittest.TestCase):
    def test_reports_local_hostname(self):
        import socket as _socket

        result = NetworkInfoTool().run()
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertIn(_socket.gethostname(), str(result.data))


class TestProcessList(unittest.TestCase):
    def test_lists_own_process(self):
        result = ProcessListTool().run(filter="")
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertIn(str(os.getpid()), str(result.tables))

    def test_filter_reduces_results(self):
        everything = ProcessListTool().run(filter="")
        only_python = ProcessListTool().run(filter="python")
        total_all = everything.tables[0].rows
        total_filtered = only_python.tables[0].rows
        self.assertLessEqual(len(total_filtered), len(total_all))
        self.assertTrue(total_filtered)  # the test runner itself is python


if __name__ == "__main__":
    unittest.main()
