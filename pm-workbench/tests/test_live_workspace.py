"""Tests for create_live_workspace.py and workspace_layout helpers."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
CREATE = WORKBENCH / "scripts" / "create_live_workspace.py"
CHECKER = WORKBENCH / "scripts" / "check_run.py"


def run(command, *, cwd=None):
    return subprocess.run(
        command, cwd=cwd, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


class CreateLiveWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_copy_mode_creates_fresh_workspace(self):
        dest = self.base / "pm-live-copy"
        result = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((dest / ".claude" / "commands" / "capture.md").is_file())
        self.assertTrue((dest / "scripts" / "check_run.py").is_file())
        self.assertFalse((dest / ".git").exists())
        self.assertFalse((dest / ".mcp.json").exists())
        for name in ("inbox", "registers", "state", "logs", "reference", "outputs"):
            path = dest / name
            self.assertTrue(path.is_dir(), name)
            self.assertFalse(path.is_symlink(), name)
        self.assertIn("id,date,decision", (dest / "registers" / "decisions.csv").read_text())
        self.assertIn("timestamp,workflow", (dest / "logs" / "run-log.csv").read_text())
        # Source working data must not have been copied even if present on kit root.
        self.assertFalse((dest / "inbox" / "meetings" / "2026-07-14-roadmap-review.txt").exists())

    def test_dev_links_mode_symlinks_kit_and_keeps_real_data_dirs(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        dest = self.base / "pm-live-links"
        result = run([sys.executable, str(CREATE), str(dest), "--dev-links"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((dest / ".claude").is_symlink())
        self.assertEqual(Path(os.readlink(dest / ".claude")), WORKBENCH / ".claude")
        self.assertTrue((dest / "scripts").is_symlink())
        for name in ("inbox", "registers", "state", "logs", "reference", "outputs"):
            self.assertTrue((dest / name).is_dir())
            self.assertFalse((dest / name).is_symlink(), name)
        self.assertFalse((dest / ".mcp.json").exists())

    def test_nonempty_destination_refuses_without_partial_writes(self):
        dest = self.base / "occupied"
        dest.mkdir()
        sentinel = dest / "keep-me.txt"
        sentinel.write_text("preserve\n", encoding="utf-8")
        result = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("empty", result.stderr.lower())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
        self.assertFalse((dest / ".claude").exists())
        self.assertFalse((dest / "scripts").exists())

    def test_rerun_refuses_overwrite(self):
        dest = self.base / "once"
        first = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(first.returncode, 0, first.stderr)
        second = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(second.returncode, 2)
        self.assertIn("empty", second.stderr.lower())

    def test_dry_run_writes_nothing(self):
        dest = self.base / "dry"
        result = run([sys.executable, str(CREATE), str(dest), "--dry-run"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(dest.exists())
        self.assertIn("Dry run", result.stdout)

    def test_refuses_destination_inside_kit(self):
        dest = WORKBENCH / "nested-live"
        result = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside", result.stderr.lower())
        self.assertFalse(dest.exists())

    def test_check_run_from_generated_workspace_targets_that_workspace(self):
        dest = self.base / "check-target"
        created = run([sys.executable, str(CREATE), str(dest)])
        self.assertEqual(created.returncode, 0, created.stderr)
        root_probe = run([
            sys.executable, "-c",
            "import os, runpy, sys;\n"
            "sys.argv = ['check_run.py', '--all'];\n"
            # Import only enough to evaluate ROOT the way check_run.py does.
            f"__file__ = {repr(str(dest / 'scripts' / 'check_run.py'))};\n"
            "ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)));\n"
            "print(ROOT);\n",
        ], cwd=str(dest))
        self.assertEqual(root_probe.returncode, 0, root_probe.stderr)
        self.assertEqual(root_probe.stdout.strip(), str(dest))
        # Invoking the script from the live folder must not crash before checks.
        result = run([sys.executable, "scripts/check_run.py", "--all"], cwd=str(dest))
        self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
        self.assertNotIn(str(WORKBENCH), result.stdout)

    def test_docs_mention_create_live_workspace_cli(self):
        new_user = (WORKBENCH / "NEW-USER-SETUP.md").read_text(encoding="utf-8")
        start = (WORKBENCH / "START HERE.md").read_text(encoding="utf-8")
        readme = (WORKBENCH.parent / "README.md").read_text(encoding="utf-8")
        for text in (new_user, start, readme):
            self.assertIn("create_live_workspace.py", text)
        self.assertIn("--dev-links", new_user)
        self.assertIn("--dry-run", new_user)
        self.assertIn("first workspace folder", new_user)


if __name__ == "__main__":
    unittest.main()
