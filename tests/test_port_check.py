"""Port check tests: deterministic loopback open/closed cases."""
from __future__ import annotations

import socket
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.port_check import PortCheckTool  # noqa: E402


def _free_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class TestPortCheck(unittest.TestCase):
    def setUp(self):
        self.tool = PortCheckTool()

    def test_validation(self):
        self.assertEqual(self.tool.validate(target="127.0.0.1", port=443), [])
        self.assertTrue(self.tool.validate(target="", port=443))
        self.assertTrue(self.tool.validate(target="127.0.0.1", port=0))
        self.assertTrue(self.tool.validate(target="127.0.0.1", port=70000))

    def test_open_port(self):
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            # generous timeout + retry: under full-suite load the first
            # loopback connect may be stalled by the OS for seconds
            result = None
            for _attempt in range(3):
                result = self.tool.run(target="127.0.0.1", port=port, timeout=5)
                if result.status is ToolStatus.SUCCESS:
                    break
        finally:
            listener.close()
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertTrue(result.summary)

    def test_closed_port(self):
        port = _free_port()  # bound+closed above -> nothing listens now
        result = self.tool.run(target="127.0.0.1", port=port, timeout=2)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn(str(port), result.summary)

    def test_unresolvable_host(self):
        result = self.tool.run(target="nonexistent.invalid", port=443, timeout=2)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
