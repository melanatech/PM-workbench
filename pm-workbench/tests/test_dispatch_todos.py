"""Tests for scripts/dispatch_todos.py — parallel drafts, no register writes."""
import csv
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import dispatch_todos  # noqa: E402


def _plan(items, *, approved=False, mode="plan", day="2026-10-14"):
    payload = {"date": day, "approved": approved, "mode": mode, "items": items, "skipped": []}
    approved_line = "yes" if approved else "no"
    lines = [
        f"# Dispatch plan {day}",
        "",
        "Status: PENDING APPROVAL",
        f"Approved: {approved_line}",
        "",
        "| id | deliverable | files | gaps | output | size |",
        "|---|---|---|---|---|---|",
    ]
    for item in items:
        lines.append(
            f"| {item['id']} | {item['deliverable']} | {'; '.join(item['files'])} | "
            f"{'; '.join(item['gaps']) or 'none'} | {item['output']} | {item['size']} |"
        )
    lines.extend(["", "```todo-plan", json.dumps(payload, indent=2), "```", ""])
    return "\n".join(lines)


def _item(todo_id, *, gaps=None):
    return {
        "id": todo_id,
        "description": f"Ask support about {todo_id}",
        "deliverable": "message",
        "files": ["inbox/meetings/q.md"],
        "gaps": gaps or [],
        "output": f"outputs/todo-drafts/{todo_id}-ask-support.md",
        "size": "short",
        "note": "",
        "links": "",
    }


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "registers").mkdir()
        self.register = self.root / "registers" / "todos.csv"
        self.register.write_text(
            "id,description,owner,due_date,priority,status,initiative,blocks,links,"
            "origin,source,created,last_updated,note\n"
            "TODO-001,Ask support,me,2026-10-09,normal,open,,,,stated,,2026-10-01,2026-10-01,\n"
            "TODO-002,Check retries,me,,low,open,,,,stated,,2026-10-01,2026-10-01,\n",
            encoding="utf-8",
        )
        self.before = self.register.read_text(encoding="utf-8")
        self.log = self.root / "dispatch-log.txt"
        self.claude = self.root / "fake-claude"
        self.claude.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import os, sys, time
            from pathlib import Path
            prompt = sys.argv[sys.argv.index("-p") + 1]
            output = ""
            for line in prompt.splitlines():
                if line.startswith("OUTPUT_PATH:"):
                    output = line.split(":", 1)[1].strip()
            log = Path(os.environ["DISPATCH_LOG"])
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"start {time.time():.6f} {output}\\n")
            time.sleep(0.4)
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("DRAFT — not sent\\n", encoding="utf-8")
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"end {time.time():.6f} {output}\\n")
            """), encoding="utf-8")
        self.claude.chmod(self.claude.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *args):
        env = os.environ.copy()
        env["DISPATCH_LOG"] = str(self.log)
        return subprocess.run(
            [sys.executable, str(WORKBENCH / "scripts" / "dispatch_todos.py"), *args],
            cwd=self.root, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_unapproved_plan_does_not_run(self):
        path = self.root / "plan.md"
        path.write_text(_plan([_item("TODO-001")]), encoding="utf-8")
        result = self._run(str(path), "--root", str(self.root), "--claude", str(self.claude))
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("not approved", result.stderr)
        self.assertFalse(self.log.exists())
        self.assertEqual(self.register.read_text(encoding="utf-8"), self.before)

    def test_parallel_workers_write_only_their_drafts(self):
        path = self.root / "plan.md"
        path.write_text(
            _plan([_item("TODO-001"), _item("TODO-002")], approved=True),
            encoding="utf-8",
        )
        result = self._run(str(path), "--root", str(self.root), "--claude", str(self.claude), "--yes")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(self.register.read_text(encoding="utf-8"), self.before)
        for todo_id in ("TODO-001", "TODO-002"):
            draft = self.root / "outputs" / "todo-drafts" / f"{todo_id}-ask-support.md"
            self.assertEqual(draft.read_text(encoding="utf-8"), "DRAFT — not sent\n")
        events = []
        for line in self.log.read_text(encoding="utf-8").splitlines():
            kind, stamp, _output = line.split(" ", 2)
            events.append((float(stamp), kind))
        events.sort()
        self.assertEqual([kind for _stamp, kind in events[:2]], ["start", "start"])
        self.assertIn("dispatched=2", result.stdout)

    def test_unattended_skips_gaps_and_leaves_status(self):
        path = self.root / "plan.md"
        path.write_text(
            _plan(
                [_item("TODO-001"), _item("TODO-002", gaps=["[NEEDS INPUT: no source file or register links]"])],
                mode="sweep",
            ),
            encoding="utf-8",
        )
        result = self._run(
            str(path), "--root", str(self.root), "--claude", str(self.claude), "--unattended",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((self.root / "outputs" / "todo-drafts" / "TODO-001-ask-support.md").is_file())
        self.assertFalse((self.root / "outputs" / "todo-drafts" / "TODO-002-ask-support.md").exists())
        self.assertTrue((self.root / "outputs" / "todo-drafts" / "2026-10-14-sweep.md").is_file())
        self.assertEqual(self.register.read_text(encoding="utf-8"), self.before)
        with self.register.open(encoding="utf-8", newline="") as handle:
            statuses = [row["status"] for row in csv.DictReader(handle)]
        self.assertEqual(statuses, ["open", "open"])


if __name__ == "__main__":
    unittest.main()
