"""TLS tool tests.

A self-signed local server is created with the OpenSSL CLI when present;
this exercises the full TLS code path (handshake, verification failure,
unverified certificate decode) without any external network.
"""
from __future__ import annotations

import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.tls_info import TlsInfoTool, _decode_der_certificate  # noqa: E402


def _find_openssl() -> str:
    candidates = [shutil.which("openssl") or ""]
    git = shutil.which("git")
    if git:  # Git for Windows bundles openssl under usr/bin
        candidates.append(str(Path(git).parent.parent / "usr" / "bin" / "openssl.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return ""


OPENSSL = _find_openssl()


class TestTlsValidation(unittest.TestCase):
    def setUp(self):
        self.tool = TlsInfoTool()

    def test_inputs(self):
        self.assertEqual(self.tool.validate(target="example.com", port=443), [])
        self.assertTrue(self.tool.validate(target="", port=443))
        self.assertTrue(self.tool.validate(target="example.com", port=0))
        self.assertTrue(self.tool.validate(target="example.com", port=-5))

    def test_connection_refused_is_clean_error(self):
        result = self.tool.run(target="127.0.0.1", port=1)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertTrue(result.summary)
        self.assertFalse(result.ok)


@unittest.skipUnless(OPENSSL, "OpenSSL CLI not available on this machine")
class TestTlsWithLocalServer(unittest.TestCase):
    def test_self_signed_cert_is_reported_as_unverified_with_details(self):
        # retry: s_server startup on a busy/headless runner can be slow
        last_error = None
        for _attempt in range(3):
            try:
                self._run_case()
                return
            except AssertionError as exc:
                last_error = exc
                time.sleep(1)
        raise last_error

    def _run_case(self) -> None:
        tool = TlsInfoTool()
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "key.pem"
            cert = Path(tmp) / "cert.pem"
            subprocess.run(
                [OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                 "-keyout", str(key), "-out", str(cert), "-days", "1",
                 "-subj", "/CN=localhost"],
                check=True, capture_output=True,
            )
            probe = socket.socket()
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
            probe.close()

            server = subprocess.Popen(
                [OPENSSL, "s_server", "-accept", str(port),
                 "-cert", str(cert), "-key", str(key), "-quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.time() + 20
                while time.time() < deadline:
                    try:
                        socket.create_connection(("127.0.0.1", port), timeout=1).close()
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise AssertionError("openssl s_server exited early")
                        time.sleep(0.3)

                result = tool.run(target="127.0.0.1", port=port)
            finally:
                server.terminate()
                server.wait(timeout=10)

        self.assertEqual(result.status, ToolStatus.ERROR)  # untrusted cert
        flattened = str(result.data)
        self.assertIn("localhost", flattened)

    def test_decode_helper_handles_garbage(self):
        self.assertEqual(_decode_der_certificate(b"not a cert"), {})


if __name__ == "__main__":
    unittest.main()
