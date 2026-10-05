"""Tests for Plan D: scripts/run_scheduled.py guardrails, /todo sweep + queue wiring, loop file, router pause."""
import csv
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
WRAPPER = WORKBENCH / "scripts" / "run_scheduled.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        shutil.copy(WRAPPER, self.root / "scripts" / "run_scheduled.py")
        self.fake = self.root / "fake_claude.py"
        write(self.fake, "#!/usr/bin/env python3\nimport os, sys\n"
              "open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calls.txt'), 'a').write(sys.argv[2] + '\\n')\n"
              "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self._tmp.cleanup()

    def run_task(self, *args, exit_code="0"):
        env = os.environ.copy()
        env["FAKE_EXIT"] = exit_code
        return subprocess.run([sys.executable, str(self.root / "scripts" / "run_scheduled.py"), *args,
                               "--claude", str(self.fake)], cwd=self.root, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def calls(self):
        path = self.root / "calls.txt"
        return path.read_text().splitlines() if path.exists() else []

    def log(self):
        with open(self.root / "logs" / "scheduled-runs.csv", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_runs_the_command_and_logs_it(self):
        result = self.run_task("daily-brief")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["/brief daily-brief"])
        self.assertEqual(self.log()[0]["status"], "ok")
        self.assertFalse((self.root / "state" / ".scheduled.lock").exists())

    def test_inbox_watch_runs_two_prompts_in_order(self):
        self.run_task("inbox-watch")
        self.assertEqual(self.calls(), ["/capture process-inbox", "/todo propose queue"])

    def test_pause_file_stops_everything(self):
        write(self.root / "state" / "PAUSE", "")
        result = self.run_task("daily-brief")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.log()[0]["status"], "skipped-paused")

    def test_daily_cap(self):
        for _ in range(2):
            self.run_task("daily-brief", "--max-runs-per-day", "2")
        self.run_task("daily-brief", "--max-runs-per-day", "2")
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(self.log()[-1]["status"], "skipped-cap")

    def test_failure_is_logged_blocked_and_stops_the_sequence(self):
        result = self.run_task("inbox-watch", exit_code="3")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.calls(), ["/capture process-inbox"])
        self.assertEqual(self.log()[0]["status"], "failed")
        with open(self.root / "logs" / "run-log.csv", newline="", encoding="utf-8") as handle:
            row = list(csv.DictReader(handle))[0]
        self.assertEqual(row["workflow"], "scheduled:inbox-watch")
        self.assertIn("BLOCKED:", row["note"])

    def test_fresh_lock_skips_and_stale_lock_is_taken(self):
        lock = self.root / "state" / ".scheduled.lock"
        write(lock, "123")
        self.run_task("daily-brief")
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.log()[-1]["status"], "skipped-running")
        old = lock.stat().st_mtime - 3 * 60 * 60
        os.utime(lock, (old, old))
        self.run_task("daily-brief")
        self.assertEqual(self.calls(), ["/brief daily-brief"])

    def test_if_new_inbox_runs_once_per_new_file(self):
        write(self.root / "inbox" / "exports" / "a.txt", "one")
        self.run_task("inbox-watch", "--if-new-inbox")
        self.assertEqual(len(self.calls()), 2)
        self.run_task("inbox-watch", "--if-new-inbox")
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(self.log()[-1]["status"], "skipped-nothing-new")
        write(self.root / "inbox" / "exports" / "b.txt", "two")
        self.run_task("inbox-watch", "--if-new-inbox")
        self.assertEqual(len(self.calls()), 4)

    def test_if_new_inbox_ignores_dotfiles(self):
        write(self.root / "inbox" / ".DS_Store", "x")
        self.run_task("inbox-watch", "--if-new-inbox")
        self.assertEqual(self.calls(), [])

    def test_failed_run_does_not_mark_inbox_as_seen(self):
        write(self.root / "inbox" / "a.txt", "one")
        self.run_task("inbox-watch", "--if-new-inbox", exit_code="1")
        self.assertFalse((self.root / "state" / "inbox-seen.json").exists())

    def test_command_has_no_prompts_and_a_narrow_allow_list(self):
        result = self.run_task("todo-sweep", "--dry-run")
        self.assertEqual(result.returncode, 0)
        for text in ("--permission-mode dontAsk", "rule 22", "never Deep"):
            self.assertIn(text, result.stdout)
        self.assertNotIn("--permission-prompts", result.stdout)
        self.assertNotIn("--dangerously-skip-permissions", result.stdout)
        self.assertNotIn("--bare", result.stdout)
        allowed = result.stdout.split("--allowedTools")[1].split()[0].strip("'")
        for broad in ("Write", "Edit", "Bash"):
            self.assertNotIn(broad + ",", allowed + ",")
        self.assertFalse((self.root / "logs").exists())

    def test_unknown_task_and_missing_claude(self):
        self.assertEqual(self.run_task("nope").returncode, 2)
        env = os.environ.copy()
        missing = subprocess.run([sys.executable, str(self.root / "scripts" / "run_scheduled.py"), "daily-brief",
                                  "--claude", "definitely-not-installed"], cwd=self.root, env=env, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(self.log()[-1]["exit_code"], "127")

    def test_every_task_prompt_names_a_real_command(self):
        sys.path.insert(0, str(WORKBENCH / "scripts"))
        import importlib
        module = importlib.import_module("run_scheduled")
        commands = {p.stem for p in (WORKBENCH / ".claude" / "commands").glob("*.md")}
        routes = json.loads((WORKBENCH / ".claude" / "workflows" / "routes.json").read_text())["clusters"]
        for task, prompts in module.TASKS.items():
            for prompt in prompts:
                words = prompt.split()
                self.assertIn(words[0].lstrip("/"), commands, task)
                if words[0].lstrip("/") in routes:
                    self.assertIn(words[1], routes[words[0].lstrip("/")], task)
        deep = {"prd-package", "experiment-package", "strategy-refresh"}
        for prompts in module.TASKS.values():
            for prompt in prompts:
                self.assertFalse(deep & set(prompt.split()))


class WiringTests(unittest.TestCase):
    def read(self, relative):
        return (WORKBENCH / relative).read_text(encoding="utf-8")

    def test_todo_command_documents_sweep_and_queue(self):
        text = self.read(".claude/commands/todo.md")
        for needle in ("`sweep`", "propose queue", "outputs/todo-proposals/", "at most **three**",
                       "Never change a to-do's status"):
            self.assertIn(needle, text)

    def test_router_protocol_has_pause_switch(self):
        self.assertIn("state/PAUSE", self.read(".claude/workflows/_protocol.md"))

    def test_loop_file_exists_and_respects_pause(self):
        text = self.read(".claude/loop.md")
        self.assertIn("state/PAUSE", text)
        self.assertIn("/todo sweep", text)
        self.assertLess(len(text.encode()), 25000)

    def test_scheduling_doc_covers_both_lanes(self):
        text = self.read("SCHEDULING.md")
        for needle in ("/loop", "run_scheduled.py", "state/PAUSE", "crontab", "Task Scheduler", "launchd"):
            self.assertIn(needle, text)
        self.assertNotIn("Routines → New routine", text)


if __name__ == "__main__":
    unittest.main()
