"""Plan E Part 1: decisions.csv `supersedes` column, the active view, the hook, migration, reset, metrics."""
import csv
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPTS = WORKBENCH / "scripts"
HOOK = WORKBENCH / ".claude" / "hooks" / "validate_register_write.py"
sys.path.insert(0, str(SCRIPTS))
import register_view  # noqa: E402

OLD_HEADER = "id,date,decision,made_by,source_link,affects"
HEADER = OLD_HEADER + ",supersedes"


def rows_of(text):
    return list(csv.DictReader(io.StringIO(text)))


def csv_text(lines, header=HEADER):
    return header + "\n" + "\n".join(lines) + "\n"


CHAIN = csv_text([
    "DEC-001,2026-10-01,Ship weekly,me,a.md,cadence,",
    "DEC-002,2026-10-05,Ship biweekly,me,b.md,cadence,DEC-001",
    "DEC-003,2026-10-09,Ship monthly,me,c.md,cadence,DEC-002",
    "DEC-004,2026-10-09,Use CSV export,me,d.md,export,",
])


class ResolutionTests(unittest.TestCase):
    def test_chain_leaves_only_the_newest_active(self):
        active = [r["id"] for r in register_view.active_rows(rows_of(CHAIN))]
        self.assertEqual(active, ["DEC-003", "DEC-004"])

    def test_multi_id_supersedes(self):
        text = csv_text(["DEC-001,2026-10-01,A,me,,x,", "DEC-002,2026-10-02,B,me,,y,",
                         "DEC-003,2026-10-03,A and B merged,me,,x,DEC-001; DEC-002"])
        self.assertEqual([r["id"] for r in register_view.active_rows(rows_of(text))], ["DEC-003"])

    def test_history_walks_the_whole_chain(self):
        ids = [r["id"] for r in register_view.chain(rows_of(CHAIN), "DEC-002")]
        self.assertEqual(ids, ["DEC-001", "DEC-002", "DEC-003"])

    def test_problems_name_dangling_self_and_forward_links(self):
        text = csv_text(["DEC-001,2026-10-01,A,me,,x,DEC-002", "DEC-002,2026-10-02,B,me,,x,DEC-002",
                         "DEC-003,2026-10-03,C,me,,x,DEC-099"])
        found = " | ".join(register_view.problems(rows_of(text)))
        self.assertIn("DEC-001 supersedes DEC-002, which comes after it", found)
        self.assertIn("DEC-002 supersedes itself", found)
        self.assertIn("DEC-099, which does not exist", found)

    def test_file_without_column_reads_all_active(self):
        rows = rows_of(csv_text(["DEC-001,2026-10-01,A,me,,x"], OLD_HEADER))
        self.assertEqual(len(register_view.active_rows(rows)), 1)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "registers").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, text, name="decisions.csv"):
        (self.root / "registers" / name).write_text(text, encoding="utf-8")

    def script(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / name), "--root", str(self.root), *args],
                              text=True, capture_output=True, cwd=self.root)

    def hook(self, new, name="decisions.csv"):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)}
        payload = {"tool_name": "Write",
                   "tool_input": {"file_path": str(self.root / "registers" / name), "content": new}}
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                              capture_output=True, cwd=self.root, env=env)


class ViewCommandTests(WorkspaceTest):
    def test_active_and_history_commands(self):
        self.put(CHAIN)
        out = subprocess.run([sys.executable, str(SCRIPTS / "register_view.py"), "active", "decisions",
                              "--root", str(self.root)], text=True, capture_output=True)
        self.assertEqual(out.stdout.splitlines()[0], HEADER)
        self.assertEqual([r["id"] for r in rows_of(out.stdout)], ["DEC-003", "DEC-004"])
        hist = subprocess.run([sys.executable, str(SCRIPTS / "register_view.py"), "history", "decisions",
                               "--id", "DEC-001", "--root", str(self.root)], text=True, capture_output=True)
        status = {r["id"]: r["status"] for r in rows_of(hist.stdout)}
        self.assertEqual(status, {"DEC-001": "superseded by DEC-002", "DEC-002": "superseded by DEC-003",
                                  "DEC-003": "active"})

    def test_integrity_flags_recent_output_citing_superseded_id(self):
        self.put(CHAIN)
        out_dir = self.root / "outputs" / "weekly"
        out_dir.mkdir(parents=True)
        (out_dir / "update.md").write_text("Cadence per DEC-002.\n", encoding="utf-8")
        (out_dir / "ok.md").write_text("DEC-001 was superseded by DEC-003.\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "register_view.py"), "integrity", "decisions",
                                 "--root", str(self.root)], text=True, capture_output=True)
        self.assertIn("outputs/weekly/update.md cites DEC-002", result.stdout)
        self.assertNotIn("ok.md", result.stdout)
        self.assertEqual(result.returncode, 0)


class HookTests(WorkspaceTest):
    OLD = csv_text(["DEC-001,2026-10-01,A,me,,x", "DEC-002,2026-10-02,B,me,,y"], OLD_HEADER)

    def test_one_time_header_migration_is_allowed(self):
        self.put(self.OLD)
        migrated = csv_text(["DEC-001,2026-10-01,A,me,,x,", "DEC-002,2026-10-02,B,me,,y,"])
        self.assertEqual(self.hook(migrated).returncode, 0, self.hook(migrated).stderr)

    def test_migration_that_changes_a_row_is_blocked(self):
        self.put(self.OLD)
        bad = csv_text(["DEC-001,2026-10-01,A,me,,x,", "DEC-002,2026-10-02,B,me,,y,DEC-001"])
        self.assertEqual(self.hook(bad).returncode, 2)

    def test_append_with_valid_link_allowed_dangling_and_self_blocked(self):
        base = csv_text(["DEC-001,2026-10-01,A,me,,x,"])
        self.put(base)
        self.assertEqual(self.hook(base + "DEC-002,2026-10-02,B,me,,x,DEC-001\n").returncode, 0)
        dangling = self.hook(base + "DEC-002,2026-10-02,B,me,,x,DEC-077\n")
        self.assertEqual(dangling.returncode, 2)
        self.assertIn("DEC-077", dangling.stderr)
        self.assertEqual(self.hook(base + "DEC-002,2026-10-02,B,me,,x,DEC-002\n").returncode, 2)

    def test_link_to_archived_id_allowed(self):
        arch = self.root / "archive" / "registers-2026-10-20"
        arch.mkdir(parents=True)
        (arch / "decisions.csv").write_text(csv_text(["DEC-040,2026-09-01,Old,me,,x,"]), encoding="utf-8")
        base = csv_text(["DEC-050,2026-10-01,A,me,,x,"])
        self.put(base)
        self.assertEqual(self.hook(base + "DEC-051,2026-10-02,B,me,,x,DEC-040\n").returncode, 0)

    def test_dropping_rows_still_blocked_without_todays_archive(self):
        self.put(CHAIN)
        self.assertEqual(self.hook(csv_text(["DEC-003,2026-10-09,Ship monthly,me,c.md,cadence,DEC-002"])).returncode, 2)


class MigrationTests(WorkspaceTest):
    LIVE = csv_text([
        "DEC-008,2026-10-05,Use the old filter,me,,filters",
        '"DEC-009",2026-10-06,"Reverses DEC-008: use the new filter",me,,filters',
        "DEC-010,2026-10-07,Consistent with DEC-008 on naming,me,,naming",
    ], OLD_HEADER)

    def test_dry_run_proposes_and_writes_nothing(self):
        self.put(self.LIVE)
        before = (self.root / "registers" / "decisions.csv").read_bytes()
        out = self.script("propose_supersedes.py")
        self.assertIn("| DEC-009 | DEC-008 | reverse |", out.stdout)
        self.assertNotIn("| DEC-010 |", out.stdout)
        self.assertEqual((self.root / "registers" / "decisions.csv").read_bytes(), before)
        self.assertFalse((self.root / "state").exists())

    def test_add_column_then_apply_approved_link(self):
        self.put(self.LIVE)
        self.assertEqual(self.script("propose_supersedes.py", "--add-column").returncode, 0)
        rows = rows_of((self.root / "registers" / "decisions.csv").read_text())
        self.assertEqual([r["supersedes"] for r in rows], ["", "", ""])
        self.assertEqual(rows[1]["decision"], "Reverses DEC-008: use the new filter")
        self.assertEqual(self.script("propose_supersedes.py", "--apply", "DEC-009=DEC-008").returncode, 0)
        rows = rows_of((self.root / "registers" / "decisions.csv").read_text())
        self.assertEqual([r["id"] for r in register_view.active_rows(rows)], ["DEC-009", "DEC-010"])
        self.assertEqual(len(list((self.root / "state" / "backups").glob("decisions-*.csv"))) >= 1, True)
        bad = self.script("propose_supersedes.py", "--apply", "DEC-008=DEC-010")
        self.assertEqual(bad.returncode, 1)


class ResetTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.put(CHAIN)
        self.put("id,description,owner,due_date,priority,status,initiative,blocks,links,origin,source,created,"
                 "last_updated,note\nTODO-001,Old,me,,normal,done,,,,stated,,2026-09-01,2026-09-01,\n"
                 "TODO-002,Live,me,,normal,open,,,,stated,,2026-10-01,2026-10-01,\n"
                 "TODO-003,Done last,me,,normal,done,,,,stated,,2026-10-02,2026-10-02,\n", "todos.csv")
        self.put("evidence_id,capture_date\nEV-001,2026-10-01\n", "evidence.csv")

    def test_dry_run_writes_nothing_and_carries_highest_id(self):
        before = {p.name: p.read_bytes() for p in (self.root / "registers").iterdir()}
        out = self.script("register_reset.py", "--today", "2026-11-02")
        self.assertIn("DEC-003", out.stdout)
        self.assertNotIn("- [x] DEC-001", out.stdout)
        self.assertIn("TODO-003 — keep (sequence)", out.stdout)
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "registers").iterdir()}, before)
        self.assertFalse((self.root / "archive").exists())

    def test_apply_archives_byte_for_byte_and_keeps_ids(self):
        before = {p.name: p.read_bytes() for p in (self.root / "registers").iterdir()}
        keep = self.root / "keep.txt"
        keep.write_text("- [x] DEC-003 — note mentions DEC-001\nDEC-004\nTODO-002\nTODO-003\n", encoding="utf-8")
        today = datetime.date.today().isoformat()
        self.assertEqual(self.script("register_reset.py", "--apply", "--keep", str(keep)).returncode, 0)
        arch = self.root / "archive" / f"registers-{today}"
        self.assertEqual({p.name: p.read_bytes() for p in arch.iterdir() if p.suffix == ".csv"}, before)
        decisions = rows_of((self.root / "registers" / "decisions.csv").read_text())
        self.assertEqual([r["id"] for r in decisions], ["DEC-003", "DEC-004"])
        self.assertEqual(decisions[0]["supersedes"], "DEC-002")
        todos = rows_of((self.root / "registers" / "todos.csv").read_text())
        self.assertEqual([r["id"] for r in todos], ["TODO-002", "TODO-003"])
        self.assertEqual((self.root / "registers" / "evidence.csv").read_text().count("\n"), 1)
        self.assertIn("registers were reset", (self.root / "reference/context/current-priorities.md").read_text())
        self.assertIn("register-reset", (self.root / "logs/run-log.csv").read_text())
        fresh = (self.root / "registers" / "decisions.csv").read_text()
        self.assertEqual(self.hook(fresh + "DEC-005,2026-11-02,New,me,,x,DEC-001\n").returncode, 0)

    def test_hook_accepts_reset_file_only_with_todays_archive(self):
        today = datetime.date.today().isoformat()
        small = csv_text(["DEC-003,2026-10-09,Ship monthly,me,c.md,cadence,DEC-002"])
        self.assertEqual(self.hook(small).returncode, 2)
        arch = self.root / "archive" / f"registers-{today}"
        arch.mkdir(parents=True)
        (arch / "decisions.csv").write_bytes((self.root / "registers" / "decisions.csv").read_bytes())
        self.assertEqual(self.hook(small).returncode, 0, self.hook(small).stderr)


class MetricsAndFixtureTests(WorkspaceTest):
    def metrics(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "workbench_metrics.py"), "--json", "--today", "2026-10-20"],
                             text=True, capture_output=True, cwd=self.root,
                             env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)})
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_reversals_counted_from_column(self):
        self.put(CHAIN)
        data = self.metrics()
        flat = json.dumps(data)
        self.assertIn('"decisions_reversed"', flat)
        value = data.get("metrics", data).get("decisions_reversed")
        value = value.get("value") if isinstance(value, dict) else value
        self.assertEqual(value, 2)

    def test_lumenly_score_unchanged_by_column(self):
        import score_fixture
        gold = json.loads((WORKBENCH / "fixtures" / "lumenly" / "gold.json").read_text())
        row = "DEC-001,2026-07-14,Phase 1 admin-only; per-location in phase 2,me,inbox/meetings/x.txt,permissions"
        self.put(csv_text([row], OLD_HEADER))
        before = score_fixture.score(str(self.root), gold)
        self.put(csv_text([row + ","]))
        self.assertEqual(score_fixture.score(str(self.root), gold), before)


class NoRawCurrentStateReads(unittest.TestCase):
    WRITERS_AND_HISTORY = {
        "workflows/experiment-analyze.md", "workflows/return-brief.md", "workflows/roadmap-update.md",
        "workflows/process-inbox.md", "workflows/monthly-review.md", "workflows/_operator-rules.md",
    }
    READERS = ["workflows/weekly-update.md", "workflows/jira-reconcile.md", "skills/authority-lookup/SKILL.md",
               "agents/prd-context-gatherer.md", "workflows/ripple-check.md", "workflows/meeting-prep.md",
               "workflows/context-reconcile.md", "workflows/meeting-closeout.md"]

    def test_only_writers_and_history_name_the_raw_file(self):
        base = WORKBENCH / ".claude"
        for path in base.rglob("*.md"):
            rel = path.relative_to(base).as_posix()
            if "registers/decisions.csv" in path.read_text(encoding="utf-8") and rel not in self.WRITERS_AND_HISTORY:
                self.fail(f"{rel} reads registers/decisions.csv directly; use register_view.py active decisions")

    def test_readers_use_the_active_view(self):
        for rel in self.READERS:
            self.assertIn("register_view.py active decisions", (WORKBENCH / ".claude" / rel).read_text(), rel)

    def test_new_workspace_header_has_column(self):
        from workspace_layout import REGISTER_HEADERS
        self.assertEqual(REGISTER_HEADERS["decisions.csv"], HEADER)


if __name__ == "__main__":
    unittest.main()
