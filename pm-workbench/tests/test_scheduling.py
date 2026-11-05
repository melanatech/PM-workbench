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


class WrapperBase(unittest.TestCase):
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

    def run_task(self, *args, exit_code="0", extra_env=None):
        env = os.environ.copy()
        env["FAKE_EXIT"] = exit_code
        env["HOME"] = str(self.root)
        env.pop("ANTHROPIC_BASE_URL", None)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(self.root / "scripts" / "run_scheduled.py"), *args,
                               "--claude", str(self.fake)], cwd=self.root, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def calls(self):
        path = self.root / "calls.txt"
        return path.read_text().splitlines() if path.exists() else []

    def log(self):
        with open(self.root / "logs" / "scheduled-runs.csv", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


class WrapperTests(WrapperBase):
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
        for task, command in module.SCRIPT_TASKS.items():
            self.assertTrue((WORKBENCH / command[0]).is_file(), task)
            self.assertNotIn(task, module.TASKS)


class RunGuardTests(WrapperBase):
    """C4 (2026-11-02): hung runs held the lock, offline wakes failed, budget errors read as generic failures."""

    def closed_port(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def test_hung_run_times_out_blocks_and_releases_lock(self):
        write(self.fake, "#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n")
        result = self.run_task("daily-brief", "--timeout-minutes", "0.02")
        self.assertEqual(result.returncode, 1)
        row = self.log()[-1]
        self.assertEqual((row["status"], row["exit_code"]), ("failed", "124"))
        self.assertFalse((self.root / "state" / ".scheduled.lock").exists())
        with open(self.root / "logs" / "run-log.csv", newline="", encoding="utf-8") as handle:
            self.assertIn("was stopped", list(csv.DictReader(handle))[0]["note"])

    def test_unreachable_gateway_skips_offline_without_running(self):
        url = f"http://127.0.0.1:{self.closed_port()}/"
        result = self.run_task("daily-brief", extra_env={"ANTHROPIC_BASE_URL": url, "PM_SCHED_PROBE_WAIT": "0"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.log()[-1]["status"], "skipped-offline")
        self.assertFalse((self.root / "logs" / "run-log.csv").exists())

    def test_gateway_read_from_claude_settings(self):
        write(self.root / ".claude" / "settings.json",
              json.dumps({"env": {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{self.closed_port()}/"}}))
        self.run_task("daily-brief", extra_env={"PM_SCHED_PROBE_WAIT": "0"})
        self.assertEqual(self.log()[-1]["status"], "skipped-offline")
        self.run_task("daily-brief", "--no-probe")
        self.assertEqual(self.calls(), ["/brief daily-brief"])

    def test_reachable_gateway_runs(self):
        import socket
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(5)
        try:
            url = f"http://127.0.0.1:{server.getsockname()[1]}/"
            self.run_task("daily-brief", extra_env={"ANTHROPIC_BASE_URL": url})
        finally:
            server.close()
        self.assertEqual(self.calls(), ["/brief daily-brief"])

    def test_once_per_day_skips_after_ok_but_retries_after_failure(self):
        self.run_task("daily-brief", "--once-per-day", exit_code="1")
        self.run_task("daily-brief", "--once-per-day")
        self.run_task("daily-brief", "--once-per-day")
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual([r["status"] for r in self.log()], ["failed", "ok", "skipped-done-today"])

    def test_budget_error_is_named(self):
        write(self.fake, "#!/usr/bin/env python3\nimport sys\n"
              "print('API Error: 422 ExceededBudget: over budget')\nsys.exit(1)\n")
        self.run_task("todo-sweep")
        with open(self.root / "logs" / "run-log.csv", newline="", encoding="utf-8") as handle:
            self.assertIn("over its spend budget", list(csv.DictReader(handle))[0]["note"])


class ScriptTaskTests(WrapperBase):
    """Plan E: script tasks run a kit script with no model, same pause and logging, own lock, no cap."""

    def setUp(self):
        super().setUp()
        write(self.root / "scripts" / "workbench_metrics.py",
              "import os, sys\nprint('snapshot written')\nsys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n")

    def test_script_task_runs_without_claude_and_saves_output(self):
        result = self.run_task("metrics-snapshot")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.log()[0]["status"], "ok")
        self.assertIn("snapshot written", (self.root / "state" / "scheduled" / "metrics-snapshot.txt").read_text())
        self.assertFalse((self.root / "state" / ".scheduled-script.lock").exists())

    def test_script_task_respects_pause(self):
        write(self.root / "state" / "PAUSE", "")
        self.run_task("metrics-snapshot")
        self.assertEqual(self.log()[0]["status"], "skipped-paused")
        self.assertFalse((self.root / "state" / "scheduled").exists())

    def test_script_task_ignores_the_model_lock_and_cap(self):
        write(self.root / "state" / ".scheduled.lock", "123")
        self.run_task("metrics-snapshot")
        self.assertEqual(self.log()[-1]["status"], "ok")
        (self.root / "state" / ".scheduled.lock").unlink()
        self.run_task("daily-brief", "--max-runs-per-day", "1")
        self.assertEqual(self.calls(), ["/brief daily-brief"])

    def test_script_lock_skips(self):
        write(self.root / "state" / ".scheduled-script.lock", "123")
        self.run_task("metrics-snapshot")
        self.assertEqual(self.log()[-1]["status"], "skipped-running")

    def test_script_failure_is_logged_blocked(self):
        result = self.run_task("metrics-snapshot", exit_code="4")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.log()[0]["status"], "failed")
        with open(self.root / "logs" / "run-log.csv", newline="", encoding="utf-8") as handle:
            row = list(csv.DictReader(handle))[0]
        self.assertEqual(row["workflow"], "scheduled:metrics-snapshot")
        self.assertIn("BLOCKED:", row["note"])

    def test_list_shows_both_kinds_and_dry_run_logs_nothing(self):
        listed = self.run_task("--list").stdout
        self.assertIn("daily-brief", listed)
        self.assertIn("metrics-snapshot       script: scripts/workbench_metrics.py --snapshot", listed)
        dry = self.run_task("workbench-health", "--dry-run")
        self.assertIn("scripts/workbench_health.py", dry.stdout)
        self.assertFalse((self.root / "logs").exists())


class JobHealthTests(unittest.TestCase):
    """Plan E step 5: workbench_health.py reports each installed job's last success and flags stale ones."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "live"
        self.agents = Path(self._tmp.name) / "agents"
        (self.root / "scripts").mkdir(parents=True)
        self.agents.mkdir()
        shutil.copy(WORKBENCH / "scripts" / "workbench_health.py", self.root / "scripts")
        write(self.root / "CLAUDE.md", "# kit\n")

    def tearDown(self):
        self._tmp.cleanup()

    def plist(self, task, calendar):
        import plistlib
        with open(self.agents / f"com.pm-workbench.{task}.plist", "wb") as handle:
            plistlib.dump({"Label": f"com.pm-workbench.{task}", "StartCalendarInterval": calendar}, handle)

    def health(self, rows):
        write(self.root / "logs" / "scheduled-runs.csv",
              "date,time,task,status,exit_code,seconds,note\n" + "".join(f"{r}\n" for r in rows))
        env = os.environ.copy()
        env["PM_LAUNCH_AGENTS_DIR"] = str(self.agents)
        out = subprocess.run([sys.executable, str(self.root / "scripts" / "workbench_health.py")], env=env,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.split("## Scheduled jobs")[1].split("\n## ")[0]

    def test_daily_and_weekly_staleness(self):
        import datetime
        today = datetime.date.today()
        self.plist("daily-brief", [{"Hour": 7, "Minute": 27, "Weekday": d} for d in range(1, 6)])
        self.plist("metrics-snapshot", {"Hour": 16, "Minute": 0, "Weekday": 5})
        self.plist("inbox-watch", [{"Hour": 8, "Minute": 12, "Weekday": d} for d in range(1, 6)])
        recent = (today - datetime.timedelta(days=5)).isoformat()
        old = (today - datetime.timedelta(days=4)).isoformat()
        section = self.health([f"{old},07:27:00,daily-brief,ok,0,10,",
                               f"{today.isoformat()},07:27:00,daily-brief,failed,1,10,",
                               f"{recent},16:00:00,metrics-snapshot,ok,0,1,",
                               f"{today.isoformat()},08:12:00,inbox-watch,skipped-nothing-new,,,"])
        self.assertIn("3 installed, 1 stale", section)
        self.assertIn("daily-brief: last success", section)
        self.assertRegex(section, r"daily-brief: last success .*\*\*STALE\*\*")
        self.assertNotRegex(section, r"metrics-snapshot: .*STALE")
        self.assertNotRegex(section, r"inbox-watch: .*STALE")

    def test_never_succeeded_is_stale_and_watchers_are_skipped(self):
        self.plist("todo-sweep", [{"Hour": 7, "Minute": 43, "Weekday": d} for d in range(1, 6)])
        import plistlib
        with open(self.agents / "com.pm-workbench.clip-watcher.plist", "wb") as handle:
            plistlib.dump({"Label": "com.pm-workbench.clip-watcher", "WatchPaths": ["/tmp/x"]}, handle)
        section = self.health([])
        self.assertIn("todo-sweep: last success never  **STALE**", section)
        self.assertIn("1 installed", section)
        self.assertNotIn("clip-watcher", section)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "home"
        self.root = Path(self._tmp.name) / "live"
        (self.root / "scripts").mkdir(parents=True)
        self.home.mkdir()
        shutil.copy(WRAPPER, self.root / "scripts" / "run_scheduled.py")

    def tearDown(self):
        self._tmp.cleanup()

    def install(self, *args):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        return subprocess.run(["bash", str(WORKBENCH / "scripts" / "install_schedules.sh"), "--root", str(self.root),
                               *args], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_dry_run_writes_nothing_and_measurement_is_opt_in(self):
        plain = self.install("--dry-run")
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn("com.pm-workbench.inbox-watch", plain.stdout)
        self.assertNotIn("metrics-snapshot", plain.stdout)
        both = self.install("--dry-run", "--with-measurement")
        self.assertEqual(both.returncode, 0, both.stderr)
        for label in ("com.pm-workbench.metrics-snapshot", "com.pm-workbench.workbench-health"):
            self.assertIn(label, both.stdout)
        self.assertFalse((self.home / "Library").exists())
        self.assertFalse((self.home / ".pm-workbench").exists())

    def test_dry_run_plists_are_valid(self):
        import plistlib
        out = self.install("--dry-run", "--with-measurement").stdout
        chunks = [c for c in out.split("# ") if c.strip().startswith(str(self.home))]
        self.assertEqual(len(chunks), 5)
        for chunk in chunks:
            body = chunk.split("\n", 1)[1].encode()
            data = plistlib.loads(body)
            self.assertIn(str(self.root / "scripts" / "run_scheduled.py"), data["ProgramArguments"])
        weekly = plistlib.loads([c for c in chunks if "metrics-snapshot.plist" in c][0].split("\n", 1)[1].encode())
        self.assertEqual(weekly["StartCalendarInterval"], {"Hour": 16, "Minute": 0, "Weekday": 5})
        for task in ("daily-brief", "todo-sweep"):
            data = plistlib.loads([c for c in chunks if f"{task}.plist" in c][0].split("\n", 1)[1].encode())
            self.assertEqual(data["ProgramArguments"][-1], "--once-per-day")
            self.assertEqual(sorted({s["Hour"] for s in data["StartCalendarInterval"]}), [7, 9, 11])


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
