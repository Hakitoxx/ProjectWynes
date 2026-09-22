"""HTTP header tool tests against a local HTTP server (no external network)."""
from __future__ import annotations

import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.http_headers import HttpHeadersTool  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def _respond(self):
        if self.path == "/redir":
            self.send_response(302)
            self.send_header("Location", "/final")
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("X-Wynes-Test", "yes")
        self.end_headers()

    def do_HEAD(self):
        self._respond()

    def do_GET(self):
        self._respond()

    def log_message(self, *_args):  # keep test output silent
        pass


def _run_with_retry(tool, url: str, attempts: int = 3):
    """Run the tool, retrying ONLY on timeout.

    Under full-suite load (parallel PowerShell/GUI smoke subprocesses) the
    OS can stall a loopback connect for seconds; the retried attempt still
    asserts the exact same outcome, so the test keeps its meaning.
    """
    result = None
    for _ in range(attempts):
        result = tool.run(url=url)
        if result.status is not ToolStatus.TIMEOUT:
            break
    return result


class TestHttpHeaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.tool = HttpHeadersTool()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_validation(self):
        self.assertEqual(self.tool.validate(url="https://example.com"), [])
        self.assertTrue(self.tool.validate(url=""))
        self.assertTrue(self.tool.validate(url="ftp://example.com"))
        self.assertTrue(self.tool.validate(url="javascript:alert(1)"))

    def test_head_request_success(self):
        url = f"http://127.0.0.1:{self.port}/"
        result = _run_with_retry(self.tool, url)
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertIn("200", result.summary)
        flattened = str(result.tables)
        self.assertIn("X-Wynes-Test", flattened)

    def test_redirect_is_reported(self):
        url = f"http://127.0.0.1:{self.port}/redir"
        result = _run_with_retry(self.tool, url)
        self.assertEqual(result.status, ToolStatus.SUCCESS, msg=result.error)
        self.assertIn("302", result.summary)
        self.assertIn("/final", str(result.data))

    def test_missing_host_fails_gracefully(self):
        # TCP stacks answer a dead port with RST or silence; either outcome
        # must surface as a clean failure state (ERROR or TIMEOUT), never a crash.
        result = self.tool.run(url="http://127.0.0.1:1/")
        self.assertIn(result.status, (ToolStatus.ERROR, ToolStatus.TIMEOUT))
        self.assertTrue(result.summary)


if __name__ == "__main__":
    unittest.main()
