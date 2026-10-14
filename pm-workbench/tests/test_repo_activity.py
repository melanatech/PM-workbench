"""Git metadata scan and the four code-vs-board drift checks."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import repo_activity  # noqa: E402


def git(path, *args, when=None):
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-C",
            str(path),
            *args,
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )


MAP = """# Systems map

## Ticket projects

| Key prefix | System | What it holds | Repo | Link convention | Source |
|---|---|---|---|---|---|
| ABC | tracker | app work | repos/app | A feature needs an ABC ticket and an XYZ ticket, linked to each other. | fixture |
| XYZ | tracker | api work | repos/api | Paired with ABC. | fixture |

## Wiki spaces

| Space | What lives there | Source |
|---|---|---|
| [SPACE] | [purpose] | fixture |
"""


class ParseTests(unittest.TestCase):
    def test_example_map_has_no_real_prefixes(self):
        text = (WORKBENCH / "reference/context/systems-map.example.md").read_text(encoding="utf-8")
        parsed = repo_activity.parse_systems_map(text)
        self.assertEqual(parsed["prefixes"], [])
        self.assertEqual(parsed["pairs"], [])

    def test_pair_convention_uses_named_prefixes_only(self):
        parsed = repo_activity.parse_systems_map(MAP)
        self.assertEqual(parsed["prefixes"], ["ABC", "XYZ"])
        self.assertEqual(parsed["pairs"], [("ABC", "XYZ")])


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.live = self.root / "live"
        (self.live / "reference" / "context").mkdir(parents=True)
        (self.live / "repos").mkdir()
        (self.live / "reference" / "context" / "systems-map.md").write_text(MAP, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _commit(self, repo, name, message, when):
        (repo / name).write_text(name + "\n", encoding="utf-8")
        git(repo, "add", name)
        git(repo, "commit", "-m", message, when=when)

    def test_parses_subject_body_branch_and_cursor(self):
        repo = self.live / "repos" / "app"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        self._commit(repo, "a.txt", "ABC-10: first\n\nXYZ-20 in the body", "2026-09-01T12:00:00")
        self._commit(repo, "b.txt", "Merge branch 'feature/XYZ-22'\n\nABC-11 landed", "2026-10-10T12:00:00")
        git(repo, "checkout", "-b", "feature/ABC-12-widget")
        self._commit(repo, "c.txt", "wip", "2026-10-11T12:00:00")
        git(repo, "checkout", "main")

        first = repo_activity.run_activity(
            self.live, since="2026-10-01", today=date(2026, 10, 14)
        )
        keys = {key for commit in first["commits"] for key in commit["keys"]}
        self.assertIn("ABC-11", keys)
        self.assertIn("XYZ-22", keys)
        self.assertNotIn("ABC-10", keys)
        self.assertEqual(first["since_source"], "argument")
        branch_keys = {key for item in first["branch_keys"] for key in item["keys"]}
        self.assertIn("ABC-12", branch_keys)
        self.assertIn("no remote; used local log", first["repos"][0]["note"])
        cursor = json.loads((self.live / "state" / "repo-activity-cursor.json").read_text())
        self.assertEqual(cursor["since"], "2026-10-14")

        second = repo_activity.run_activity(self.live, today=date(2026, 10, 15), fetch=False)
        self.assertEqual(second["since_source"], "cursor")
        self.assertEqual(second["since"], "2026-10-14")
        self.assertEqual(second["commits"], [])

    def test_fetch_failure_still_reads_the_local_log(self):
        repo = self.live / "repos" / "app"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        self._commit(repo, "a.txt", "ABC-10: local only", "2026-10-10T12:00:00")
        git(repo, "remote", "add", "origin", str(self.root / "missing.git"))
        snapshot = repo_activity.run_activity(
            self.live, since="2026-10-01", today=date(2026, 10, 14)
        )
        self.assertEqual(snapshot["repos"][0]["fetch"], "local-log")
        self.assertIn("fetch failed", snapshot["repos"][0]["note"])
        self.assertIn("used local log", snapshot["repos"][0]["note"])
        keys = {key for commit in snapshot["commits"] for key in commit["keys"]}
        self.assertEqual(keys, {"ABC-10"})

    def test_shallow_since_deepens_a_local_remote(self):
        origin = self.root / "origin"
        origin.mkdir()
        git(origin, "init", "-b", "main")
        self._commit(origin, "a.txt", "ABC-10: older", "2026-09-15T12:00:00")
        self._commit(origin, "b.txt", "ABC-11: tip", "2026-10-10T12:00:00")
        clone = self.live / "repos" / "app"
        # file:// forces a real shallow clone. A local path can hardlink full history.
        subprocess.run(
            ["git", "clone", "--depth", "1", f"file://{origin}", str(clone)],
            check=True,
            capture_output=True,
            text=True,
        )
        shallow = subprocess.run(
            ["git", "-C", str(clone), "rev-parse", "--is-shallow-repository"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(shallow.stdout.strip(), "true")
        snapshot = repo_activity.run_activity(
            self.live, since="2026-09-01", today=date(2026, 10, 14)
        )
        self.assertEqual(snapshot["repos"][0]["fetch"], "ok")
        keys = {key for commit in snapshot["commits"] for key in commit["keys"]}
        self.assertIn("ABC-11", keys)
        self.assertIn("ABC-10", keys)

    def test_symlink_repo_is_scanned(self):
        real = self.root / "outside"
        real.mkdir()
        git(real, "init", "-b", "main")
        self._commit(real, "a.txt", "XYZ-7: via symlink", "2026-10-10T12:00:00")
        (self.live / "repos" / "app").symlink_to(real)
        snapshot = repo_activity.run_activity(
            self.live, since="2026-10-01", today=date(2026, 10, 14), fetch=False
        )
        self.assertEqual(snapshot["repos"][0]["path"], "repos/app")
        keys = {key for commit in snapshot["commits"] for key in commit["keys"]}
        self.assertEqual(keys, {"XYZ-7"})


class DriftTests(unittest.TestCase):
    def test_four_drift_checks_are_local_tier_2(self):
        activity = {
            "commits": [
                {
                    "repo": "repos/app",
                    "sha": "aaaaaaaaaaaa1111",
                    "date": "2026-10-10",
                    "keys": ["ABC-1"],
                    "on_default_branch": True,
                },
                {
                    "repo": "repos/app",
                    "sha": "bbbbbbbbbbbb2222",
                    "date": "2026-09-01",
                    "keys": ["ABC-2"],
                    "on_default_branch": False,
                },
                {
                    "repo": "repos/app",
                    "sha": "cccccccccccc3333",
                    "date": "2026-10-12",
                    "keys": ["ABC-3"],
                    "on_default_branch": True,
                },
                {
                    "repo": "repos/app",
                    "sha": "dddddddddddd4444",
                    "date": "2026-10-12",
                    "keys": ["ABC-5"],
                    "on_default_branch": True,
                },
            ],
            "branch_keys": [
                {"repo": "repos/app", "branch": "feature/ABC-6-notes", "keys": ["ABC-6"]}
            ],
        }
        tickets = [
            {"key": "ABC-1", "status": "To Do"},
            {"key": "ABC-2", "status": "In Progress"},
            {"key": "ABC-4", "status": "Done"},
            {"key": "ABC-5", "status": "Done"},
            {"key": "ABC-7", "status": "In Progress"},
        ]
        checks = repo_activity.code_vs_board(activity, tickets, stale_days=7, today=date(2026, 10, 14))
        by_check = {}
        for item in checks:
            by_check.setdefault(item["check"], set()).add(item["key"])
            self.assertEqual(item["tier"], 2)
            self.assertFalse(item["tracker_write"])
            self.assertEqual(item["batch"], "code-vs-board")
        self.assertEqual(by_check["merged_but_open"], {"ABC-1"})
        self.assertEqual(by_check["stale_in_progress"], {"ABC-2", "ABC-7"})
        self.assertEqual(by_check["key_not_on_board"], {"ABC-3", "ABC-6"})
        self.assertEqual(by_check["done_without_commits"], {"ABC-4"})
        done = next(item for item in checks if item["key"] == "ABC-4")
        self.assertEqual(done["priority"], "low")
        self.assertIn("non-code", done["evidence"])
        self.assertEqual(repo_activity.code_vs_board(activity, []), [])


if __name__ == "__main__":
    unittest.main()
