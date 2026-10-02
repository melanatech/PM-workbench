"""Tests for Plan C: scripts/workbench_metrics.py, output-hash recording, log-proposal, score_fixture.py."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
METRICS = WORKBENCH / "scripts" / "workbench_metrics.py"
SCORER = WORKBENCH / "scripts" / "score_fixture.py"
TODO_SCRIPT = WORKBENCH / "scripts" / "todo_register.py"
PROVENANCE_HOOK = WORKBENCH / ".claude" / "hooks" / "check_output_provenance.py"
GOLD = WORKBENCH / "fixtures" / "lumenly" / "gold.json"
TODAY = "2026-10-02"


def run(command, *, cwd=None, env=None, input_text=None):
    return subprocess.run(command, cwd=cwd, env=env, input=input_text, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Workspace(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        for script in (METRICS, TODO_SCRIPT):
            shutil.copy(script, self.root / "scripts" / script.name)

    def tearDown(self):
        self._tmp.cleanup()

    def metrics(self, *flags):
        result = run([sys.executable, str(self.root / "scripts" / "workbench_metrics.py"),
                      "--today", TODAY, *flags], cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def values(self):
        return json.loads(self.metrics("--json"))["metrics"]


class MetricTests(Workspace):
    def test_missing_sources_are_na_not_zero(self):
        values = self.values()
        self.assertIsNone(values["commitments_overdue"])
        self.assertIsNone(values["todos_open"])
        self.assertIsNone(values["decisions_30d"])
        self.assertIn("n/a", self.metrics())

    def test_commitments_overdue_ignores_closed_and_undated(self):
        write(self.root / "registers" / "commitments.csv",
              "id,commitment,due_date,status\n"
              "COM-001,a,2026-09-01,open\n"
              "COM-002,b,2026-09-01,done\n"
              "COM-003,c,,open\n"
              "COM-004,d,2026-12-01,open\n")
        self.assertEqual(self.values()["commitments_overdue"], 1)

    def test_todo_counts(self):
        header = "id,description,owner,due_date,priority,status,initiative,blocks,links,origin,source,created,last_updated,note\n"
        write(self.root / "registers" / "todos.csv", header +
              "TODO-001,a,me,2026-09-01,normal,open,,,,stated,,2026-09-02,2026-09-02,\n"
              "TODO-002,b,me,,normal,blocked,,,,stated,,2026-09-22,2026-09-22,\n"
              "TODO-003,c,me,,normal,done,,,,stated,,2026-09-01,2026-09-25,\n"
              "TODO-004,d,me,,normal,dropped,,,,stated,,2026-06-01,2026-06-02,\n")
        values = self.values()
        self.assertEqual(values["todos_open"], 2)
        self.assertEqual(values["todos_overdue"], 1)
        self.assertEqual(values["todos_blocked"], 1)
        self.assertEqual(values["todos_done_30d"], 1)
        self.assertEqual(values["todos_dropped_30d"], 0)
        self.assertEqual(values["todos_median_age"], 20)

    def test_decision_quality_counts(self):
        write(self.root / "registers" / "decisions.csv",
              "id,date,decision,made_by,source_link\n"
              "DEC-001,2026-09-20,Ship A,maya,inbox/a.md\n"
              "DEC-002,2026-09-25,Ship B,,\n"
              "DEC-003,2026-09-28,This supersedes DEC-001,maya,inbox/b.md\n"
              "DEC-004,2026-05-01,Old one,maya,\n")
        values = self.values()
        self.assertEqual(values["decisions_30d"], 3)
        self.assertEqual(values["decisions_no_source_30d"], 1)
        self.assertEqual(values["decisions_no_owner_30d"], 1)
        self.assertEqual(values["decisions_reversed"], 1)

    def test_stale_initiatives_and_missing_decision_link(self):
        write(self.root / "registers" / "initiatives.csv",
              "id,name,stage,last_updated,related_decisions\n"
              "INIT-001,a,build,2026-08-01,DEC-001\n"
              "INIT-002,b,build,2026-09-30,\n"
              "INIT-003,c,launched,2026-01-01,\n")
        values = self.values()
        self.assertEqual(values["initiatives_stale"], 1)
        self.assertEqual(values["stage_without_decision"], 1)

    def test_repeat_runs_exclude_cadence_workflows(self):
        write(self.root / "logs" / "run-log.csv",
              "timestamp,workflow,success,note\n"
              "2026-09-20T09:00:00,build:prd-package,yes,\n"
              "2026-09-22T09:00:00,build:prd-package,yes,\n"
              "2026-09-20T08:00:00,brief:daily-brief,yes,\n"
              "2026-09-21T08:00:00,brief:daily-brief,yes,\n"
              "2026-09-23T08:00:00,sync:ripple-check,blocked,BLOCKED: no export\n")
        values = self.values()
        self.assertEqual(values["runs_30d"], 5)
        self.assertEqual(values["repeat_runs_30d"], 1)
        self.assertEqual(values["blocked_runs"], 1)

    def test_unattended_metrics(self):
        write(self.root / "logs" / "scheduled-runs.csv",
              "date,time,task,status,exit_code,seconds,note\n"
              "2026-09-30,07:30:00,daily-brief,ok,0,40,\n"
              "2026-10-01,07:30:00,daily-brief,failed,1,10,\n"
              "2026-10-01,18:00:00,inbox-watch,skipped-nothing-new,,,\n"
              "2026-10-02,07:30:00,daily-brief,skipped-paused,,,\n"
              "2026-06-01,07:30:00,daily-brief,ok,0,40,\n")
        write(self.root / "outputs" / "todo-drafts" / "TODO-001-a.md", "DRAFT\n")
        values = self.values()
        self.assertEqual(values["scheduled_runs_30d"], 2)
        self.assertEqual(values["scheduled_failed_30d"], 1)
        self.assertEqual(values["scheduled_skipped_30d"], 1)

    def test_proposals_are_summed_over_30_days(self):
        write(self.root / "logs" / "todo-proposals.csv",
              "date,source,offered,accepted\n2026-09-20,a,5,3\n2026-09-25,b,4,1\n2026-06-01,c,9,9\n")
        values = self.values()
        self.assertEqual(values["proposals_offered"], 9)
        self.assertEqual(values["proposals_accepted"], 4)

    def test_edited_outputs_are_detected_by_hash(self):
        import hashlib
        kept, changed = self.root / "outputs" / "kept.md", self.root / "outputs" / "changed.md"
        write(kept, "same\n")
        write(changed, "before\n")
        digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
        write(self.root / "state" / "output-hashes.csv",
              "path,sha256,written_at\n"
              f"outputs/kept.md,{digest('same' + chr(10))},2026-09-01T00:00:00\n"
              f"outputs/changed.md,{digest('before' + chr(10))},2026-09-01T00:00:00\n"
              "outputs/gone.md,abc,2026-09-01T00:00:00\n")
        changed.write_text("after, edited by hand\n", encoding="utf-8")
        values = self.values()
        self.assertEqual(values["outputs_tracked"], 2)
        self.assertEqual(values["outputs_edited"], 1)


class SnapshotTests(Workspace):
    def history(self):
        with open(self.root / "state" / "health-history.csv", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_snapshot_writes_one_row_per_day_and_marks_baseline(self):
        out = self.metrics("--snapshot")
        self.assertIn("No snapshot recorded yet", out)
        self.metrics("--snapshot")
        rows = self.history()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], TODAY)
        self.assertEqual(rows[0]["todos_open"], "")
        self.assertIn("provisional", self.metrics())

    def test_change_column_after_baseline(self):
        write(self.root / "registers" / "commitments.csv",
              "id,commitment,due_date,status\nCOM-001,a,2026-07-01,open\nCOM-002,b,2026-07-02,open\n")
        run([sys.executable, str(self.root / "scripts" / "workbench_metrics.py"),
             "--today", "2026-08-01", "--snapshot"], cwd=self.root)
        write(self.root / "registers" / "commitments.csv",
              "id,commitment,due_date,status\nCOM-001,a,2026-07-01,open\nCOM-002,b,2026-07-02,done\n")
        out = self.metrics()
        self.assertIn("Baseline captured 2026-08-01", out)
        self.assertIn("-1 (better)", out)

    def test_snapshot_refuses_symlinked_state(self):
        target = self.root / "elsewhere"
        target.mkdir()
        os.symlink(target, self.root / "state")
        result = run([sys.executable, str(self.root / "scripts" / "workbench_metrics.py"),
                      "--today", TODAY, "--snapshot"], cwd=self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(target.iterdir()), [])


class HashHookTests(unittest.TestCase):
    def test_hook_records_hash_for_outputs_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "registers").mkdir()
            write(root / "outputs" / "plan.md", "Hello.\n")
            write(root / "reference" / "note.md", "Not an output.\n")
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(root)
            for name in ("outputs/plan.md", "reference/note.md"):
                payload = {"tool_name": "Write", "tool_input": {"file_path": str(root / name)}}
                result = run([sys.executable, str(PROVENANCE_HOOK)], cwd=root, env=env,
                             input_text=json.dumps(payload))
                self.assertEqual(result.returncode, 0, result.stderr)
            with open(root / "state" / "output-hashes.csv", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([r["path"] for r in rows], ["outputs/plan.md"])
            self.assertEqual(len(rows[0]["sha256"]), 64)


class LogProposalTests(Workspace):
    def log(self, *args):
        return run([sys.executable, str(self.root / "scripts" / "todo_register.py"), "log-proposal",
                    "--today", TODAY, *args], cwd=self.root)

    def test_appends_with_header(self):
        self.assertEqual(self.log("--offered", "5", "--accepted", "2", "--source", "inbox/a.md").returncode, 0)
        self.assertEqual(self.log("--offered", "3", "--accepted", "0").returncode, 0)
        lines = (self.root / "logs" / "todo-proposals.csv").read_text().splitlines()
        self.assertEqual(lines[0], "date,source,offered,accepted")
        self.assertEqual(lines[1], f"{TODAY},inbox/a.md,5,2")
        self.assertEqual(len(lines), 3)

    def test_rejects_accepted_above_offered(self):
        result = self.log("--offered", "1", "--accepted", "2")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "logs" / "todo-proposals.csv").exists())


class ScoreFixtureTests(unittest.TestCase):
    def score(self, decisions="", commitments="", risks=""):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "registers" / "decisions.csv", "id,date,decision\n" + decisions)
            write(root / "registers" / "commitments.csv", "id,date,commitment\n" + commitments)
            write(root / "registers" / "risks.csv", "id,date_raised,risk,status\nRISK-008,2026-07-16,preloaded,watch\n" + risks)
            result = run([sys.executable, str(SCORER), "--root", str(root), "--gold", str(GOLD), "--json"])
            return result.returncode, json.loads(result.stdout)

    GOOD_D = "DEC-001,2026-07-14,Phase 1 is admin-only; per-location in phase 2\n"
    GOOD_C = "COM-001,2026-07-14,Maya updates the PRD audience section by Wednesday\n"
    GOOD_R = "RISK-009,2026-07-15,Mobile team may deprioritize (secondhand and unconfirmed),open\n"

    def test_perfect_run_passes(self):
        code, out = self.score(self.GOOD_D, self.GOOD_C, self.GOOD_R)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["pass"])

    def test_missing_items_are_reported(self):
        code, out = self.score(self.GOOD_D)
        self.assertEqual(code, 1)
        self.assertEqual(len(out["registers"]["commitments"]["missed"]), 1)
        self.assertEqual(len(out["registers"]["risks"]["missed"]), 1)

    def test_invented_row_date_and_forbidden_text_fail(self):
        code, out = self.score(self.GOOD_D + "DEC-002,2026-01-01,Approved by leadership: ship it\n", self.GOOD_C, self.GOOD_R)
        self.assertEqual(code, 1)
        invented = " ".join(out["registers"]["decisions"]["invented"])
        self.assertIn("matches no expected", invented)
        self.assertIn("not in the fixture", invented)
        self.assertIn("forbidden", invented)

    def test_risk_stated_as_fact_fails(self):
        code, out = self.score(self.GOOD_D, self.GOOD_C, "RISK-009,2026-07-15,Mobile team will deprioritize this,open\n")
        self.assertEqual(code, 1)
        self.assertIn("no unconfirmed marker", " ".join(out["registers"]["risks"]["invented"]))


if __name__ == "__main__":
    unittest.main()
