"""Regression tests for check_run.py's successful-run file inventory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
CHECKER = WORKBENCH / "scripts" / "check_run.py"
LOADER = WORKBENCH / "scripts" / "load_fixture.py"


def run(command, *, cwd=None):
    return subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )


class DeletedFileTests(unittest.TestCase):
    def make_workspace(self, root):
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "check_run.py").write_bytes(CHECKER.read_bytes())

    def baseline(self, root, files):
        marker = root / "state/.last-check"
        marker.parent.mkdir(parents=True, exist_ok=True)
        inventory = {
            path: hashlib.sha256(content).hexdigest()
            for path, content in files.items()
        }
        marker.write_text(json.dumps({
            "checked_at": "2026-07-20T12:00:00",
            "cutoff": time.time(),
            "run_log_rows": 0,
            "inventory": inventory,
        }), encoding="utf-8")
        return marker, inventory

    def test_deletion_with_old_mtime_fails_and_is_repeated_from_retained_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_workspace(root)
            deleted = root / "inbox/old-capture.txt"
            deleted.parent.mkdir()
            content = b"captured input\n"
            deleted.write_bytes(content)
            old_time = time.time() - 7200
            os.utime(deleted, (old_time, old_time))
            marker, expected_inventory = self.baseline(
                root, {"inbox/old-capture.txt": content}
            )
            deleted.unlink()
            original_marker = marker.read_bytes()

            first = run([sys.executable, "scripts/check_run.py"], cwd=root)
            second = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            self.assertIn("inbox/old-capture.txt: file was deleted", first.stdout)
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
            self.assertIn("inbox/old-capture.txt: file was deleted", second.stdout)
            self.assertEqual(marker.read_bytes(), original_marker)
            self.assertEqual(json.loads(marker.read_text())["inventory"], expected_inventory)

    def test_unchanged_inbox_file_moved_to_archive_is_not_a_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_workspace(root)
            source = root / "inbox/capture.txt"
            source.parent.mkdir()
            content = b"unchanged source material\n"
            source.write_bytes(content)
            old_time = time.time() - 7200
            os.utime(source, (old_time, old_time))
            marker, _ = self.baseline(root, {"inbox/capture.txt": content})
            destination = root / "archive/capture.txt"
            destination.parent.mkdir()
            os.replace(source, destination)

            result = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("deleted", result.stdout)
            inventory = json.loads(marker.read_text(encoding="utf-8"))["inventory"]
            self.assertNotIn("inbox/capture.txt", inventory)
            self.assertEqual(inventory["archive/capture.txt"], hashlib.sha256(content).hexdigest())

    def test_isolated_fixture_loader_seeds_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            isolated = Path(temporary) / "fictional-workbench"

            result = run([
                sys.executable, str(LOADER), "lumenly", "--isolate", str(isolated)
            ])

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            marker = json.loads((isolated / "state/.last-check").read_text(encoding="utf-8"))
            expected_path = "inbox/meetings/2026-07-14-roadmap-review.txt"
            self.assertIn(expected_path, marker["inventory"])
            self.assertNotIn("state/.last-check", marker["inventory"])
            self.assertEqual(
                marker["inventory"][expected_path],
                hashlib.sha256((isolated / expected_path).read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()