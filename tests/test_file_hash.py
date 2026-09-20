"""File hash tests: correctness vs hashlib, chunking, formatting."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wynes.core.tool_base import ToolStatus  # noqa: E402
from wynes.tools.file_hash import ALGORITHMS, FileHashTool, format_size, hash_file  # noqa: E402


class TestHashFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, data: bytes) -> str:
        path = self.dir / name
        path.write_bytes(data)
        return str(path)

    def test_known_sha256(self):
        path = self._write("a.bin", b"abc")
        digest, size, _elapsed = hash_file(path, "sha256")
        self.assertEqual(digest, hashlib.sha256(b"abc").hexdigest())
        self.assertEqual(size, 3)

    def test_large_file_chunked_read(self):
        data = os.urandom(5 * 1024 * 1024 + 12345)  # > several 1 MiB chunks
        path = self._write("big.bin", data)
        digest, size, _ = hash_file(path, "sha512")
        self.assertEqual(digest, hashlib.sha512(data).hexdigest())
        self.assertEqual(size, len(data))

    def test_empty_file(self):
        path = self._write("empty.bin", b"")
        digest, size, _ = hash_file(path, "md5")
        self.assertEqual(digest, hashlib.md5(b"").hexdigest())
        self.assertEqual(size, 0)

    def test_every_algorithm_runs_through_tool(self):
        path = self._write("t.bin", b"wynes")
        tool = FileHashTool()
        for algorithm in ALGORITHMS:
            result = tool.run(path=path, algorithm=algorithm)
            self.assertEqual(result.status, ToolStatus.SUCCESS, msg=algorithm)
            expected = hashlib.new(algorithm, b"wynes").hexdigest()
            self.assertIn(expected, str(result.data))

    def test_missing_file_is_validation_error(self):
        tool = FileHashTool()
        self.assertTrue(tool.validate(path=str(self.dir / "nope.bin")))

    def test_format_size(self):
        self.assertEqual(format_size(512), "512 B")
        self.assertTrue(format_size(2048).startswith("2.0 KB"))
        self.assertTrue(format_size(3 * 1024 * 1024).startswith("3.0 MB"))


if __name__ == "__main__":
    unittest.main()
