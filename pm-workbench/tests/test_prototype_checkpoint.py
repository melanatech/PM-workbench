#!/usr/bin/env python3
"""Tests for prototype_checkpoint.py."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "prototype_checkpoint.py"


class PrototypeCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-ckpt-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.proto = self.tmp / "prototypes" / "demo"
        self.proto.mkdir(parents=True)
        (self.proto / "index.html").write_text("<h1>v1</h1>\n", encoding="utf-8")

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_checkpoint_and_restore_by_label(self):
        r1 = self.run_script("--path", str(self.proto), "--label", "after-scaffold")
        self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
        (self.proto / "index.html").write_text("<h1>v2</h1>\n", encoding="utf-8")
        r2 = self.run_script("--path", str(self.proto), "--label", "after-qa")
        self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
        log = self.tmp / "logs" / "prototype-checkpoints" / "demo.md"
        self.assertTrue(log.is_file(), "expected log outside prototype git tree")
        self.assertIn("after-scaffold", log.read_text(encoding="utf-8"))
        r3 = self.run_script("--path", str(self.proto), "--restore", "after-scaffold")
        self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
        self.assertIn(
            "<h1>v1</h1>", (self.proto / "index.html").read_text(encoding="utf-8")
        )

    def test_refuses_path_outside_prototypes(self):
        other = self.tmp / "elsewhere"
        other.mkdir()
        r = self.run_script("--path", str(other), "--label", "x")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
