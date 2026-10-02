"""Tests for the /todo register: hook, run checker and scripts/todo_register.py (stdlib only)."""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "todo_register.py"
CHECKER = WORKBENCH / "scripts" / "check_run.py"
REGISTER_HOOK = WORKBENCH / ".claude" / "hooks" / "validate_register_write.py"
PROVENANCE_HOOK = WORKBENCH / ".claude" / "hooks" / "check_output_provenance.py"
SEED = WORKBENCH / "fixtures" / "lumenly" / "registers" / "todos.csv"

HEADER = ("id,description,owner,due_date,priority,status,initiative,blocks,links,"
          "origin,source,created,last_updated,note")
ROW1 = "TODO-001,Ask support,me,2026-10-09,normal,open,,,,stated,,2026-10-01,2026-10-01,"
ROW2 = "TODO-002,Check retries,me,,low,open,,,,stated,,2026-10-01,2026-10-01,"
BASE = f"{HEADER}\n{ROW1}\n{ROW2}\n"


def run(command, *, cwd=None, env=None, input_text=None):
    return subprocess.run(command, cwd=cwd, env=env, input=input_text, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


class TodoHookTests(unittest.TestCase):
    def invoke(self, existing, updated):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "registers" / "todos.csv"
            path.parent.mkdir()
            path.write_text(existing, encoding="utf-8")
            payload = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": updated}}
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(root)
            return run([sys.executable, str(REGISTER_HOOK)], cwd=root, env=env,
                       input_text=json.dumps(payload))

    def test_in_place_edit_and_append_are_allowed(self):
        edited = BASE.replace("2026-10-09,normal,open", "2026-10-12,high,in_progress")
        self.assertEqual(self.invoke(BASE, edited).returncode, 0)
        appended = BASE + "TODO-003,New one,me,,normal,open,,,,stated,,2026-10-02,2026-10-02,\n"
        self.assertEqual(self.invoke(BASE, appended).returncode, 0)

    def test_header_change_is_blocked(self):
        result = self.invoke(BASE, BASE.replace("description", "desc", 1))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("HEADER", result.stderr)

    def test_removed_row_is_blocked(self):
        result = self.invoke(BASE, f"{HEADER}\n{ROW1}\n")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("lose rows", result.stderr)

    def test_reordered_ids_are_blocked(self):
        result = self.invoke(BASE, f"{HEADER}\n{ROW2}\n{ROW1}\n")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_duplicate_id_is_blocked(self):
        result = self.invoke(BASE, BASE + ROW1 + "\n")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("duplicate id", result.stderr)

    def test_multiline_cell_is_blocked(self):
        broken = BASE.replace("Ask support", '"Ask\nsupport"')
        result = self.invoke(BASE, broken)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("line break", result.stderr)

    def test_wrong_field_count_is_blocked(self):
        result = self.invoke(BASE, BASE + "TODO-003,Has a comma, unquoted,me\n")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("fields", result.stderr)


class TodoCheckerTests(unittest.TestCase):
    def workspace(self, root, register=BASE):
        (root / "scripts").mkdir()
        shutil.copy(CHECKER, root / "scripts" / "check_run.py")
        (root / "registers").mkdir()
        (root / "registers" / "todos.csv").write_text(register, encoding="utf-8")
        (root / "outputs").mkdir()

    def check(self, root, text):
        (root / "outputs" / "draft.md").write_text(text, encoding="utf-8")
        return run([sys.executable, "scripts/check_run.py", "--all"], cwd=root)

    def test_valid_todo_id_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.workspace(root)
            result = self.check(root, "Follow up on TODO-001 (draft, not sent).\n")
            self.assertNotIn("TODO-001", "\n".join(l for l in result.stdout.splitlines() if "FAIL" in l),
                             result.stdout)

    def test_invented_todo_id_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.workspace(root)
            result = self.check(root, "This depends on TODO-777 (draft).\n")
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("TODO-777", result.stdout)

    def test_todo_id_is_not_treated_as_a_ticket_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.workspace(root)
            result = self.check(root, "See TODO-001 and TODO-002 (draft).\n")
            self.assertNotIn("ticket", result.stdout.lower().replace("ticket keys cited", ""), result.stdout)

    def test_output_provenance_hook_flags_invented_todo_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.workspace(root)
            target = root / "outputs" / "plan.md"
            target.write_text("Blocked by TODO-555.\n", encoding="utf-8")
            payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(root)
            result = run([sys.executable, str(PROVENANCE_HOOK)], cwd=root, env=env,
                         input_text=json.dumps(payload))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("TODO-555", result.stderr)
            target.write_text("Blocked by TODO-001.\n", encoding="utf-8")
            ok = run([sys.executable, str(PROVENANCE_HOOK)], cwd=root, env=env,
                     input_text=json.dumps(payload))
            self.assertEqual(ok.returncode, 0, ok.stderr)


class TodoScriptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        shutil.copy(SCRIPT, self.root / "scripts" / "todo_register.py")
        (self.root / "registers").mkdir()
        self.register = self.root / "registers" / "todos.csv"

    def tearDown(self):
        self._tmp.cleanup()

    def todo(self, *args, input_text=None):
        return run([sys.executable, "scripts/todo_register.py", *args], cwd=self.root, input_text=input_text)

    def seed(self, text=BASE):
        self.register.write_text(text, encoding="utf-8")

    def test_add_creates_register_with_next_id_and_defaults(self):
        first = self.todo("add", "--description", "First", "--today", "2026-10-02")
        second = self.todo("add", "--description", "Second", "--today", "2026-10-02", "--priority", "high")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        rows = read_rows(self.register)
        self.assertEqual([r[0] for r in rows[1:]], ["TODO-001", "TODO-002"])
        self.assertEqual(rows[1][2:6], ["me", "", "normal", "open"])
        self.assertEqual(rows[1][9], "stated")
        self.assertEqual(rows[2][4], "high")
        self.assertEqual(rows[1][11:13], ["2026-10-02", "2026-10-02"])

    def test_add_needs_description_and_valid_date_and_priority(self):
        self.assertEqual(self.todo("add").returncode, 1)
        self.assertEqual(self.todo("add", "--description", "x", "--due", "10/09").returncode, 1)
        self.assertEqual(self.todo("add", "--description", "x", "--priority", "urgent").returncode, 1)
        self.assertFalse(self.register.exists())

    def test_comma_and_quote_values_round_trip_through_stdin(self):
        text = 'Ask the team about "silent" failures, then report back'
        result = self.todo("add", "--stdin", "--today", "2026-10-02",
                           input_text=json.dumps({"description": text, "links": "EV-211, RISK-008"}))
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = read_rows(self.register)
        self.assertEqual(len(rows[1]), 14)
        self.assertEqual(rows[1][1], text)
        self.assertEqual(rows[1][8], "EV-211, RISK-008")

    def test_multiline_values_are_collapsed(self):
        self.todo("add", "--description", "line one\nline two", "--today", "2026-10-02")
        self.assertEqual(read_rows(self.register)[1][1], "line one line two")

    def test_update_changes_only_named_fields_in_place(self):
        self.seed()
        result = self.todo("update", "TODO-001", "--due", "2026-10-15", "--status", "in_progress",
                           "--today", "2026-10-03")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = read_rows(self.register)
        self.assertEqual([r[0] for r in rows[1:]], ["TODO-001", "TODO-002"])
        self.assertEqual(rows[1][3], "2026-10-15")
        self.assertEqual(rows[1][5], "in_progress")
        self.assertEqual(rows[1][1], "Ask support")
        self.assertEqual(rows[1][11], "2026-10-01")
        self.assertEqual(rows[1][12], "2026-10-03")
        self.assertEqual(rows[2], ROW2.split(","))

    def test_update_can_clear_a_date_and_refuses_origin_and_bad_status(self):
        self.seed()
        self.assertEqual(self.todo("update", "TODO-001", "--due", "").returncode, 0)
        self.assertEqual(read_rows(self.register)[1][3], "")
        self.assertEqual(self.todo("update", "TODO-001", "--origin", "proposed").returncode, 1)
        self.assertEqual(self.todo("update", "TODO-001", "--status", "done").returncode, 1)
        self.assertEqual(self.todo("update", "TODO-099", "--note", "x").returncode, 1)
        self.assertEqual(self.todo("update", "TODO-001").returncode, 1)

    def test_bare_number_resolves_to_id(self):
        self.seed()
        self.assertEqual(self.todo("update", "2", "--note", "hi").returncode, 0)
        self.assertEqual(read_rows(self.register)[2][13], "hi")

    def test_done_keeps_the_row_and_reopen_works(self):
        self.seed()
        self.assertEqual(self.todo("done", "TODO-001", "--note", "sent", "--today", "2026-10-04").returncode, 0)
        rows = read_rows(self.register)
        self.assertEqual(len(rows), 3)
        self.assertEqual((rows[1][5], rows[1][13], rows[1][12]), ("done", "sent", "2026-10-04"))
        self.assertEqual(self.todo("done", "TODO-001").returncode, 1)
        self.assertEqual(self.todo("update", "TODO-001", "--status", "open").returncode, 0)
        self.assertEqual(read_rows(self.register)[1][5], "open")

    def test_drop_requires_a_reason_and_never_deletes(self):
        self.seed()
        refused = self.todo("drop", "TODO-002")
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(self.register.read_text(encoding="utf-8"), BASE)
        self.assertEqual(self.todo("drop", "TODO-002", "--reason", "no longer needed").returncode, 0)
        rows = read_rows(self.register)
        self.assertEqual(len(rows), 3)
        self.assertEqual((rows[2][0], rows[2][5], rows[2][13]), ("TODO-002", "dropped", "no longer needed"))
        self.todo("update", "TODO-002", "--status", "open")
        self.todo("drop", "TODO-002", "--reason", "again")
        self.assertEqual(read_rows(self.register)[2][13], "no longer needed | again")

    def test_list_filters_use_the_today_override(self):
        self.seed(BASE + "TODO-003,Done thing,me,2026-10-01,normal,done,,,,stated,,2026-09-20,2026-10-01,\n"
                  + "TODO-004,Blocked thing,me,2026-10-05,high,blocked,,,,stated,,2026-09-20,2026-09-20,\n")

        def ids(*args):
            out = self.todo("list", "--json", *args)
            self.assertEqual(out.returncode, 0, out.stderr)
            return [r["id"] for r in json.loads(out.stdout)["rows"]]

        self.assertEqual(ids("--filter", "overdue", "--today", "2026-10-10"), ["TODO-004", "TODO-001"])
        self.assertEqual(ids("--filter", "overdue", "--today", "2026-10-01"), [])
        self.assertEqual(ids("--filter", "due-today", "--today", "2026-10-09"), ["TODO-001"])
        self.assertEqual(ids("--filter", "due-week", "--today", "2026-10-03"), ["TODO-004", "TODO-001"])
        self.assertEqual(ids("--filter", "blocked", "--today", "2026-10-03"), ["TODO-004"])
        self.assertEqual(ids("--filter", "open", "--today", "2026-10-03"), ["TODO-004", "TODO-001", "TODO-002"])
        self.assertEqual(ids("--filter", "done", "--today", "2026-10-03"), ["TODO-003"])
        self.assertEqual(ids("--filter", "done", "--today", "2026-12-01"), [])
        self.assertEqual(len(ids("--filter", "all")), 4)

    def test_list_filters_by_initiative_blocks_and_id(self):
        self.seed(f"{HEADER}\n"
                  "TODO-001,A,me,,normal,open,Export Reliability,PRD for Export Reliability,,stated,,2026-10-01,2026-10-01,\n"
                  "TODO-002,B,me,,normal,open,Other,,,stated,,2026-10-01,2026-10-01,\n")
        def ids(*args):
            return [r["id"] for r in json.loads(self.todo("list", "--json", *args).stdout)["rows"]]
        self.assertEqual(ids("--initiative", "export"), ["TODO-001"])
        self.assertEqual(ids("--blocks", "prd for export"), ["TODO-001"])
        self.assertEqual(ids("--id", "2"), ["TODO-002"])

    def test_counts_line(self):
        self.seed()
        out = self.todo("counts", "--today", "2026-10-10")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("1 overdue", out.stdout)
        self.assertIn("2 open", out.stdout)
        data = json.loads(self.todo("counts", "--json", "--today", "2026-10-09").stdout)
        self.assertEqual((data["due-today"], data["overdue"], data["open"]), (1, 0, 2))

    def test_empty_register_lists_cleanly(self):
        out = self.todo("list")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("No to-dos yet", out.stdout)
        self.assertFalse(self.register.exists())

    def test_wrong_header_is_refused_untouched(self):
        bad = BASE.replace("description", "desc", 1)
        self.seed(bad)
        result = self.todo("add", "--description", "x")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.register.read_text(encoding="utf-8"), bad)

    def test_duplicate_ids_and_bad_rows_are_refused(self):
        dup = BASE + ROW1 + "\n"
        self.seed(dup)
        self.assertEqual(self.todo("add", "--description", "x").returncode, 2)
        self.assertEqual(self.register.read_text(encoding="utf-8"), dup)
        short = BASE + "TODO-003,only,three\n"
        self.seed(short)
        self.assertEqual(self.todo("done", "TODO-001").returncode, 2)

    def test_symlinked_register_is_refused_and_target_untouched(self):
        outside = self.root / "outside.csv"
        outside.write_text(BASE, encoding="utf-8")
        self.register.symlink_to(outside)
        result = self.todo("add", "--description", "x")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), BASE)

    def test_hard_linked_register_is_refused(self):
        outside = self.root / "outside.csv"
        outside.write_text(BASE, encoding="utf-8")
        os.link(outside, self.register)
        result = self.todo("add", "--description", "x")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), BASE)

    def test_result_passes_the_register_hook_and_the_checker(self):
        self.todo("add", "--description", "Ask support, then report", "--today", "2026-10-02")
        self.todo("update", "TODO-001", "--priority", "high")
        text = self.register.read_text(encoding="utf-8")
        hook = TodoHookTests()
        self.assertEqual(hook.invoke(text, text.replace("high", "low")).returncode, 0)
        self.assertEqual(len(list(csv.reader(io.StringIO(text)))[1]), 14)


class FixtureSeedTests(unittest.TestCase):
    def test_seed_matches_header_and_cites_only_fixture_ids(self):
        rows = read_rows(SEED)
        self.assertEqual(",".join(rows[0]), HEADER)
        self.assertTrue(all(len(r) == 14 for r in rows))
        cited = {x.strip() for r in rows[1:] for x in r[8].split(",") if x.strip()}
        self.assertLessEqual(cited, {"EV-211", "RISK-008"})

    def test_seed_overdue_depends_on_the_today_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "registers").mkdir()
            shutil.copy(SCRIPT, root / "scripts" / "todo_register.py")
            shutil.copy(SEED, root / "registers" / "todos.csv")
            out = run([sys.executable, "scripts/todo_register.py", "counts", "--json", "--today", "2026-07-17"], cwd=root)
            data = json.loads(out.stdout)
            self.assertEqual((data["open"], data["overdue"]), (3, 1))


if __name__ == "__main__":
    unittest.main()
