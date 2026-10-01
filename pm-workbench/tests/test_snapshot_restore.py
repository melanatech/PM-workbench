"""Restore safety regression tests (stdlib only)."""
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
RESTORE_SCRIPT = WORKBENCH / "scripts" / "restore-state.sh"


def run(command, *, cwd=None, env=None, preexec_fn=None):
    return subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, env=env, preexec_fn=preexec_fn,
    )


class SnapshotRestoreTests(unittest.TestCase):
    def make_workspace(self, root, *, create_targets=True):
        (root / "scripts").mkdir(parents=True)
        shutil.copy(RESTORE_SCRIPT, root / "scripts/restore-state.sh")
        if create_targets:
            (root / "registers").mkdir()
            (root / "logs").mkdir()
            (root / "reference/context").mkdir(parents=True)

    def make_snapshot(self, base, entries):
        snapshot = base / "backup/20260721-120000"
        for relative, content in entries.items():
            path = snapshot / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return snapshot

    def invoke(self, root, snapshot, *arguments, env=None, preexec_fn=None):
        return run(
            ["bash", "scripts/restore-state.sh", *arguments, str(snapshot)],
            cwd=root, env=env, preexec_fn=preexec_fn,
        )

    def test_dry_run_then_restore_missing_files_and_leave_identical_files_alone(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            snapshot = self.make_snapshot(base, {
                "registers/decisions.csv": "id,decision\nDEC-001,approved\n",
                "reference/context/priorities.md": "current priorities\n",
                "logs/run-log.csv": "timestamp,workflow\n",
            })
            same = root / "registers/decisions.csv"
            same.write_text("id,decision\nDEC-001,approved\n", encoding="utf-8")
            original_stat = same.stat()

            preview = self.invoke(root, snapshot, "--dry-run")

            self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
            self.assertIn("Would restore: reference/context/priorities.md", preview.stdout)
            self.assertIn("Unchanged (identical): registers/decisions.csv", preview.stdout)
            self.assertFalse((root / "logs/run-log.csv").exists())

            restored = self.invoke(root, snapshot)

            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            self.assertEqual((root / "reference/context/priorities.md").read_text(), "current priorities\n")
            self.assertEqual((root / "logs/run-log.csv").read_text(), "timestamp,workflow\n")
            self.assertEqual(same.stat().st_ino, original_stat.st_ino)
            self.assertEqual(same.stat().st_mtime_ns, original_stat.st_mtime_ns)

    def test_any_differing_file_blocks_the_entire_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            snapshot = self.make_snapshot(base, {
                "registers/a-missing.csv": "restore me\n",
                "registers/z-newer.csv": "snapshot version\n",
            })
            newer = root / "registers/z-newer.csv"
            newer.write_text("newer local record\n", encoding="utf-8")

            result = self.invoke(root, snapshot)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("existing file differs", result.stderr)
            self.assertFalse((root / "registers/a-missing.csv").exists())
            self.assertEqual(newer.read_text(encoding="utf-8"), "newer local record\n")

    def test_symlink_in_snapshot_refuses_restore_without_touching_link_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            snapshot = self.make_snapshot(base, {"registers/good.csv": "safe\n"})
            outside = base / "outside.txt"
            outside.write_text("preserve\n", encoding="utf-8")
            (snapshot / "registers/linked.csv").symlink_to(outside)

            result = self.invoke(root, snapshot)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("symlink in snapshot", result.stderr)
            self.assertFalse((root / "registers/good.csv").exists())
            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve\n")

    def test_symlink_or_hardlink_in_target_refuses_entire_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            snapshot = self.make_snapshot(base, {
                "registers/missing.csv": "must not be restored\n",
            })
            outside = base / "outside.txt"
            outside.write_text("preserve\n", encoding="utf-8")
            (root / "registers/linked.csv").symlink_to(outside)

            symlink_result = self.invoke(root, snapshot)

            self.assertEqual(symlink_result.returncode, 2, symlink_result.stderr)
            self.assertIn("symlink in restore target", symlink_result.stderr)
            self.assertFalse((root / "registers/missing.csv").exists())
            (root / "registers/linked.csv").unlink()
            os.link(outside, root / "registers/shared.txt")

            hardlink_result = self.invoke(root, snapshot)

            self.assertEqual(hardlink_result.returncode, 2, hardlink_result.stderr)
            self.assertIn("hardlinked file in restore target", hardlink_result.stderr)
            self.assertFalse((root / "registers/missing.csv").exists())
            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve\n")

    def test_snapshot_scope_is_limited_to_saved_roots_and_usage_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            snapshot = self.make_snapshot(base, {
                "registers/valid.csv": "valid\n",
                "inbox/unrelated.txt": "out of scope\n",
            })

            result = self.invoke(root, snapshot)
            usage = run(["bash", "scripts/restore-state.sh"], cwd=root)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("outside the saved state scope", result.stderr)
            self.assertFalse((root / "registers/valid.csv").exists())
            self.assertEqual(usage.returncode, 2)
            self.assertIn("Usage:", usage.stderr)
            self.assertIn("--dry-run", usage.stderr)

    def test_failed_snapshot_enumeration_never_creates_target_files_or_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root, create_targets=False)
            snapshot = self.make_snapshot(base, {
                "registers/partial.csv": "partial enumeration\n",
                "logs/also-partial.csv": "must not restore\n",
            })
            shim_dir = base / "shim"
            shim_dir.mkdir()
            find_shim = shim_dir / "find"
            find_shim.write_text(
                "#!/bin/sh\n"
                "printf '%s\\0' \"$1/registers/partial.csv\"\n"
                "echo 'simulated traversal failure' >&2\n"
                "exit 1\n",
                encoding="utf-8",
            )
            find_shim.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = str(shim_dir) + os.pathsep + environment["PATH"]

            result = self.invoke(root, snapshot, env=environment)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("enumerate the snapshot completely", result.stderr)
            self.assertFalse((root / "registers").exists())
            self.assertFalse((root / "logs").exists())
            self.assertFalse((root / "reference").exists())

    def test_permission_denied_snapshot_subtree_aborts_before_target_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root, create_targets=False)
            snapshot = self.make_snapshot(base, {
                "registers/visible.csv": "readable sibling\n",
                "registers/unreadable/hidden.csv": "not readable\n",
            })
            unreadable = snapshot / "registers/unreadable"
            unreadable.chmod(0)
            preexec_fn = None
            if os.geteuid() == 0:
                try:
                    nobody = pwd.getpwnam("nobody")
                except KeyError:
                    self.skipTest("no unprivileged test account is available")
                base.chmod(0o755)

                def drop_privileges():
                    os.setgid(nobody.pw_gid)
                    os.setuid(nobody.pw_uid)

                preexec_fn = drop_privileges

            try:
                result = self.invoke(root, snapshot, preexec_fn=preexec_fn)
            finally:
                unreadable.chmod(0o755)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("enumerate the snapshot completely", result.stderr)
            self.assertFalse((root / "registers").exists())
            self.assertFalse((root / "logs").exists())
            self.assertFalse((root / "reference").exists())

    def test_unreadable_regular_source_refuses_dry_run_and_restore_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root, create_targets=False)
            snapshot = self.make_snapshot(base, {
                "registers/a-readable.csv": "readable source\n",
                "registers/z-unreadable.csv": "unreadable source\n",
            })
            unreadable = snapshot / "registers/z-unreadable.csv"
            unreadable.chmod(0)
            preexec_fn = None
            if os.geteuid() == 0:
                try:
                    nobody = pwd.getpwnam("nobody")
                except KeyError:
                    self.skipTest("no unprivileged test account is available")
                base.chmod(0o755)

                def drop_privileges():
                    os.setgid(nobody.pw_gid)
                    os.setuid(nobody.pw_uid)

                preexec_fn = drop_privileges

            try:
                preview = self.invoke(root, snapshot, "--dry-run", preexec_fn=preexec_fn)
                restored = self.invoke(root, snapshot, preexec_fn=preexec_fn)
            finally:
                unreadable.chmod(0o644)

            self.assertEqual(preview.returncode, 2, preview.stdout + preview.stderr)
            self.assertIn("Failed to read snapshot file during preflight", preview.stderr)
            self.assertEqual(restored.returncode, 2, restored.stdout + restored.stderr)
            self.assertIn("Failed to read snapshot file during preflight", restored.stderr)
            self.assertFalse((root / "registers").exists())
            self.assertFalse((root / "logs").exists())
            self.assertFalse((root / "reference").exists())

    def test_real_snapshot_script_round_trip_restores_only_removed_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            shutil.copy(WORKBENCH / "scripts/snapshot-state.sh", root / "scripts/snapshot-state.sh")
            expected = {
                "registers/decisions.csv": "id,decision\nDEC-001,approved\n",
                "reference/context/priorities.md": "priority one\n",
                "logs/run-log.csv": "timestamp,workflow\n",
            }
            for relative, content in expected.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            backup = base / "approved-backups"
            environment = os.environ.copy()
            environment["PM_STATE_BACKUP"] = str(backup)

            created = run(["bash", "scripts/snapshot-state.sh"], cwd=root, env=environment)

            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            snapshot_line = next(
                line for line in created.stdout.splitlines()
                if line.startswith("Created a local snapshot at: ")
            )
            snapshot = Path(snapshot_line.rsplit(": ", 1)[1])
            self.assertTrue(snapshot.is_dir())
            for relative in expected:
                (root / relative).unlink()
            preserved = root / "registers/newer-local.csv"
            preserved.write_text("newer local record\n", encoding="utf-8")

            restored = self.invoke(root, snapshot)

            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            for relative, content in expected.items():
                self.assertEqual((root / relative).read_text(encoding="utf-8"), content)
            self.assertEqual(preserved.read_text(encoding="utf-8"), "newer local record\n")


if __name__ == "__main__":
    unittest.main()