"""Repeatable safety checks for the fictional first-run path (stdlib only)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
LOADER = WORKBENCH / "scripts" / "load_fixture.py"
LAYOUT = WORKBENCH / "scripts" / "workspace_layout.py"
CHECKER = WORKBENCH / "scripts" / "check_run.py"
REGISTER_HOOK = WORKBENCH / ".claude" / "hooks" / "validate_register_write.py"
SNAPSHOT_SCRIPT = WORKBENCH / "scripts" / "snapshot-state.sh"


def install_loader(scripts_dir):
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(LOADER, scripts_dir / "load_fixture.py")
    shutil.copy(LAYOUT, scripts_dir / "workspace_layout.py")


def run(command, *, cwd=None, env=None, input_text=None):
    return subprocess.run(
        command, cwd=cwd, env=env, input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


class FixtureLoaderTests(unittest.TestCase):
    def test_conflict_refuses_whole_load_without_writing_other_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            install_loader(scripts)
            shutil.copytree(WORKBENCH / "fixtures", root / "fixtures")
            target = root / "inbox/captures/capture-2026-07-16.md"
            target.parent.mkdir(parents=True)
            target.write_text("REAL WORK — preserve this\n", encoding="utf-8")

            result = run([sys.executable, "scripts/load_fixture.py", "lumenly"], cwd=root)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("conflict:", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "REAL WORK — preserve this\n")
            self.assertFalse((root / "registers/evidence.csv").exists())
            self.assertFalse((root / "state/.last-check").exists())

    def test_overwrite_never_follows_symlink_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workbench"
            root.mkdir()
            install_loader(root / "scripts")
            shutil.copytree(WORKBENCH / "fixtures", root / "fixtures")
            sentinel = Path(temporary) / "outside-sensitive-file.txt"
            sentinel.write_text("preserve outside target\n", encoding="utf-8")
            target = root / "inbox/captures/capture-2026-07-16.md"
            target.parent.mkdir(parents=True)
            target.symlink_to(sentinel)

            result = run([
                sys.executable, "scripts/load_fixture.py", "lumenly", "--overwrite"
            ], cwd=root)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("unsafe target", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve outside target\n")
            self.assertFalse((root / "registers/evidence.csv").exists())

    def test_isolated_fixture_load_leaves_source_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source-workbench"
            install_loader(source / "scripts")
            shutil.copytree(WORKBENCH / "fixtures", source / "fixtures")
            source_context = source / "reference/context/private-company-context.md"
            source_context.parent.mkdir(parents=True)
            source_context.write_text("sensitive source context\n", encoding="utf-8")
            source_capture = source / "inbox/raw-capture.md"
            source_capture.parent.mkdir(parents=True)
            source_capture.write_text("sensitive raw capture\n", encoding="utf-8")
            local_env = source / ".env.local"
            local_env.write_text("local-only setting\n", encoding="utf-8")
            before = {path: path.read_bytes() for path in (source_context, source_capture, local_env)}
            isolated = base / "fictional-workbench"

            result = run([
                sys.executable, "scripts/load_fixture.py", "lumenly", "--isolate", str(isolated)
            ], cwd=source)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("isolated copy", result.stdout)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse((isolated / "reference/context/private-company-context.md").exists())
            self.assertFalse((isolated / "inbox/raw-capture.md").exists())
            self.assertFalse((isolated / ".env.local").exists())
            self.assertTrue((isolated / "inbox/meetings/2026-07-14-roadmap-review.txt").is_file())
            self.assertTrue((isolated / "registers/evidence.csv").is_file())
            self.assertIn(
                "This week's top 3",
                (isolated / "reference/context/current-priorities.md").read_text(encoding="utf-8"),
            )


class RunCheckerTests(unittest.TestCase):
    def make_workspace(self, root):
        scripts = root / "scripts"
        scripts.mkdir()
        shutil.copy(CHECKER, scripts / "check_run.py")

    def test_refuses_a_symlinked_baseline_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            root.mkdir()
            self.make_workspace(root)
            marker = root / "state/.last-check"
            marker.parent.mkdir()
            sentinel = base / "outside-sensitive-file.txt"
            sentinel.write_text("preserve baseline target\n", encoding="utf-8")
            marker.symlink_to(sentinel)

            result = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Unsafe state/.last-check path", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve baseline target\n")

    def test_failure_keeps_legacy_baseline_so_same_finding_repeats(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_workspace(root)
            marker = root / "state/.last-check"
            marker.parent.mkdir()
            marker.write_text("legacy baseline\n", encoding="utf-8")
            old_time = time.time() - 7200
            os.utime(marker, (old_time, old_time))
            output = root / "outputs/draft.md"
            output.parent.mkdir()
            output.write_text("Draft cites RISK-999 without a register row.\n", encoding="utf-8")

            first = run([sys.executable, "scripts/check_run.py"], cwd=root)
            first_marker = (marker.read_bytes(), marker.stat().st_mtime_ns)
            second = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            self.assertIn("RISK-999", first.stdout)
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
            self.assertIn("RISK-999", second.stdout)
            self.assertIn("baseline retained", second.stdout)
            self.assertEqual((marker.read_bytes(), marker.stat().st_mtime_ns), first_marker)

    def test_first_failed_check_persists_its_initial_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_workspace(root)
            output = root / "outputs/draft.md"
            output.parent.mkdir()
            output.write_text("Draft cites EV-999 without a register row.\n", encoding="utf-8")

            first = run([sys.executable, "scripts/check_run.py"], cwd=root)
            marker = root / "state/.last-check"
            baseline = json.loads(marker.read_text(encoding="utf-8"))
            second = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            self.assertLess(baseline["cutoff"], time.time() - 25 * 60)
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
            self.assertIn("EV-999", second.stdout)

    def test_success_advances_baseline_and_requires_a_new_run_log_row_next_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_workspace(root)
            output = root / "outputs/draft.md"
            output.parent.mkdir()
            output.write_text("A plain local draft.\n", encoding="utf-8")
            log = root / "logs/run-log.csv"
            log.parent.mkdir()
            log.write_text(
                "timestamp,workflow,approx_duration,success,note\n"
                "2026-07-20T12:00:00,/meeting-closeout,1m,ok,fixture test\n",
                encoding="utf-8",
            )

            first = run([sys.executable, "scripts/check_run.py"], cwd=root)
            marker = root / "state/.last-check"

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            baseline = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(baseline["run_log_rows"], 1)

            time.sleep(0.02)
            output.write_text("A changed local draft.\n", encoding="utf-8")
            second = run([sys.executable, "scripts/check_run.py"], cwd=root)

            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
            self.assertIn("did not gain a data row", second.stdout)
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8")), baseline)


class RegisterHistoryHookTests(unittest.TestCase):
    def invoke_hook(self, root, filename, existing, updated):
        path = root / "registers" / filename
        path.parent.mkdir(exist_ok=True)
        path.write_text(existing, encoding="utf-8")
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(path), "content": updated},
        }
        environment = os.environ.copy()
        environment["CLAUDE_PROJECT_DIR"] = str(root)
        return run(
            [sys.executable, str(REGISTER_HOOK)],
            cwd=root,
            env=environment,
            input_text=json.dumps(payload),
        )

    def test_history_rows_are_immutable_but_current_state_rows_can_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            history = "id,decision\nDEC-001,approved scope\n"
            changed_history = "id,decision\nDEC-001,changed scope\n"
            appended_history = history + "DEC-002,new decision\n"
            current = "id,status\nCOM-001,open\n"
            changed_current = "id,status\nCOM-001,done\n"
            deleted_current = "id,status\n"

            blocked = self.invoke_hook(root, "decisions.csv", history, changed_history)
            appended = self.invoke_hook(root, "decisions.csv", history, appended_history)
            update = self.invoke_hook(root, "commitments.csv", current, changed_current)
            deletion = self.invoke_hook(root, "commitments.csv", current, deleted_current)

            self.assertEqual(blocked.returncode, 2, blocked.stderr)
            self.assertIn("immutable history", blocked.stderr)
            self.assertEqual(appended.returncode, 0, appended.stderr)
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertEqual(deletion.returncode, 2, deletion.stderr)
            self.assertIn("lose rows", deletion.stderr)


class SnapshotSafetyTests(unittest.TestCase):
    def make_workbench(self, root):
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy(SNAPSHOT_SCRIPT, scripts / "snapshot-state.sh")
        for relative, content in (
            ("registers/decisions.csv", "id,decision\nDEC-001,fictional\n"),
            ("reference/context/current-priorities.md", "fictional context\n"),
            ("logs/run-log.csv", "timestamp,workflow\n"),
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_snapshot_requires_explicit_non_git_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workbench"
            self.make_workbench(root)
            script = root / "scripts/snapshot-state.sh"
            environment = os.environ.copy()
            environment.pop("PM_STATE_BACKUP", None)

            missing = run(["bash", str(script)], cwd=root, env=environment)
            self.assertEqual(missing.returncode, 2, missing.stderr)
            self.assertIn("approved company-managed", missing.stderr)

            repo = base / "company-repo"
            repo.mkdir()
            git_init = run(["git", "init", "-q", str(repo)])
            if git_init.returncode:
                self.skipTest("git init unavailable; non-Git backup path test still applies")
            environment["PM_STATE_BACKUP"] = str(repo)
            refused = run(["bash", str(script)], cwd=root, env=environment)
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertIn("Git working tree", refused.stderr)
            self.assertEqual(list(repo.iterdir()), [repo / ".git"])

            bare_repo = base / "company-bare.git"
            bare_init = run(["git", "init", "--bare", "-q", str(bare_repo)])
            self.assertEqual(bare_init.returncode, 0, bare_init.stderr)
            environment["PM_STATE_BACKUP"] = str(bare_repo / "nested-backup")
            bare_refused = run(["bash", str(script)], cwd=root, env=environment)
            self.assertEqual(bare_refused.returncode, 2, bare_refused.stderr)
            self.assertIn("Git repository", bare_refused.stderr)
            self.assertFalse((bare_repo / "nested-backup" / "registers").exists())

            destination = base / "approved-company-storage"
            environment["PM_STATE_BACKUP"] = str(destination)
            created = run(["bash", str(script)], cwd=root, env=environment)
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            snapshot_dirs = [path for path in destination.iterdir() if path.is_dir()]
            self.assertEqual(len(snapshot_dirs), 1)
            snapshot = snapshot_dirs[0]
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o700)
            self.assertTrue((snapshot / "registers/decisions.csv").is_file())
            self.assertTrue((snapshot / "reference/context/current-priorities.md").is_file())
            self.assertTrue((snapshot / "logs/run-log.csv").is_file())


if __name__ == "__main__":
    unittest.main()