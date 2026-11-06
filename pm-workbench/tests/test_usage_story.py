#!/usr/bin/env python3
"""Tests for scripts/usage_story.py: synthetic usage rows and story structure."""
from __future__ import annotations

import contextlib
import csv
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import usage_story as us  # noqa: E402

FIELDS = [
    "session_id", "message_uuid", "timestamp", "user_uuid", "user_excerpt", "category",
    "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
    "surface",
]

GOOD_STORY = """# Title

## Executive summary
x
## So what
x
## What changed in how I use AI
x
## Where the effort went: corrections
x
## What it produced
x
## What the kit changed in response
x
## Cost
Estimated spend at list price is $10.00. This is an estimate.
## What we cannot claim yet
x
## Next run should check
x
## Sources
x
"""


def _row(i, day, category, excerpt="do the thing", user="u", tokens=100):
    return {
        "session_id": "s1", "message_uuid": f"m{i}", "timestamp": f"{day}T10:00:00Z",
        "user_uuid": f"{user}{i // 2}", "user_excerpt": excerpt, "category": category,
        "input_tokens": str(tokens), "output_tokens": "0",
        "cache_creation_input_tokens": "0", "cache_read_input_tokens": "0", "surface": "panel",
    }


def _live(rows, todos=None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="pmwb-story-"))
    (root / "state").mkdir()
    (root / "registers").mkdir()
    with (root / "state" / "usage-history.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    if todos is not None:
        with (root / "registers" / "todos.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "status", "created"])
            w.writeheader()
            w.writerows(todos)
    return root


def _data(root: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        us.main(["data", "--root", str(root), "--since", "2026-10-01"])
    return buf.getvalue()


class DataTests(unittest.TestCase):
    def test_subagent_results_are_not_corrections(self):
        rows = [
            _row(0, "2026-10-05", "rework_correction", "you missed the jira source"),
            _row(1, "2026-10-05", "rework_correction", "<task-notification> <result>RESULT</result>"),
            _row(2, "2026-10-05", "workflow:process-inbox"),
            _row(3, "2026-10-05", "lookup"),
        ]
        out = _data(_live(rows))
        self.assertIn("Labeled correction calls: 2", out)
        self.assertIn("(excluded): 1", out)
        self.assertIn("Real correction calls: 1 (25% of all calls)", out)
        self.assertIn("| Subagent result returned |", out)

    def test_editor_context_turns_stay_in_their_category(self):
        rows = [
            _row(0, "2026-10-05", "rework_correction",
                 "<ide_opened_file>opened x</ide_opened_file> you forgot the dates"),
            _row(1, "2026-10-05", "lookup"),
        ]
        out = _data(_live(rows))
        self.assertIn("Real correction calls: 1", out)
        self.assertNotIn("Subagent result returned", out)

    def test_weeks_state_active_days_and_split_mix(self):
        rows = [
            _row(0, "2026-10-05", "lookup"),
            _row(1, "2026-10-06", "workflow:okr-refresh"),
            _row(2, "2026-10-12", "workflow:okr-refresh"),
        ]
        out = _data(_live(rows))
        self.assertIn("Week of 2026-10-05: 2026-10-05 to 2026-10-06, 2 active days", out)
        self.assertIn("Week of 2026-10-12: 2026-10-12 to 2026-10-12, 1 active days", out)
        self.assertIn("Week of 2026-10-12: okr-refresh 1", out)
        self.assertIn("| Named workbench workflow | 50% / 50% | 100% / 100% |", out)

    def test_todos_report_done_count_and_no_cost(self):
        todos = [
            {"id": "T1", "status": "done", "created": "2026-10-05"},
            {"id": "T2", "status": "open", "created": "2026-10-06"},
        ]
        out = _data(_live([_row(0, "2026-10-05", "lookup")], todos))
        self.assertIn("Done: 1 of 2", out)
        self.assertNotIn("$", out)

    def test_corrections_per_pm_message_with_coverage(self):
        rows = [
            _row(0, "2026-10-05", "rework_correction", "that's wrong"),
            _row(1, "2026-10-05", "rework_correction", "that's wrong"),
            _row(2, "2026-10-05", "other"),
            _row(3, "2026-10-05", "rework_correction", "<task-notification> x", user="n"),
            {**_row(4, "2026-10-05", "rework_correction", "wrong"), "user_uuid": ""},
        ]
        out = _data(_live(rows))
        self.assertIn(
            "Week of 2026-10-05: corrections 1 of 2 PM messages (50%); coverage 1 of 2 (50%); "
            "among labeled 1 of 1 (100%)",
            out,
        )

    def test_returns_past_the_stale_session_line(self):
        first = _row(0, "2026-10-05", "lookup", tokens=90000)
        cold = _row(2, "2026-10-05", "lookup", tokens=1000)
        cold["timestamp"] = "2026-10-05T11:30:00Z"
        cold["cache_creation_input_tokens"] = "90000"
        forced = _row(4, "2026-10-05", "lookup", "!force keep going", tokens=1000)
        forced["timestamp"] = "2026-10-05T13:00:00Z"
        forced["cache_read_input_tokens"] = "90000"
        short = _row(6, "2026-10-05", "lookup", tokens=1000)
        short["timestamp"] = "2026-10-05T13:30:00Z"
        env = {"SESSION_MEMORY_IDLE_MINUTES": "60", "SESSION_MEMORY_MIN_TOKENS": "80000"}
        with mock.patch.dict(os.environ, env):
            out = _data(_live([first, cold, forced, short]))
        self.assertIn("Line: 60+ minutes since the previous reply and 80,000+ tokens", out)
        self.assertIn("!force stays in the median", out)
        self.assertIn("reply scored is the one in the same chat", out)
        self.assertNotIn("!force returns left out", out)
        self.assertNotIn("on the rest", out)
        self.assertIn(
            "Week of 2026-10-05: 2 returns in 1 chats; cold 1; started with !force 1; "
            "median from-scratch tokens: 45,000",
            out,
        )
        self.assertIn(
            "All rows in this file: 2 eligible returns; started with !force 1; "
            "median from-scratch tokens: 45,000",
            out,
        )

    def test_empty_usage_says_how_to_fill(self):
        root = Path(tempfile.mkdtemp(prefix="pmwb-story-empty-"))
        self.assertIn("--backfill", _data(root))


class CheckTests(unittest.TestCase):
    def test_complete_story_passes(self):
        self.assertEqual(us.check_story(GOOD_STORY), [])

    def test_missing_summary_and_so_what_fail(self):
        story = GOOD_STORY.replace("## Executive summary\nx\n## So what\nx\n", "")
        problems = us.check_story(story)
        self.assertIn("missing section: executive summary", problems)
        self.assertIn("missing section: so what", problems)
        self.assertIn("first section must be the executive summary", problems)

    def test_cost_first_story_fails(self):
        story = "# T\n\n## Cost\nx\n" + GOOD_STORY.split("\n", 1)[1]
        self.assertIn("first section must be the executive summary", us.check_story(story))

    def test_spend_per_artifact_fails(self):
        for line in ("About $2.07 per output file.", "That is $1.67/decision.", "$3 per row"):
            problems = us.check_story(GOOD_STORY + line + "\n")
            self.assertTrue(any("artifact count" in p for p in problems), line)

    def test_dashboard_rate_per_billion_tokens_is_allowed(self):
        self.assertEqual(us.check_story(GOOD_STORY + "| $10 per billion tokens |\n"), [])

    def test_sample_postmortem_passes(self):
        text = (WORKBENCH / "fixtures" / "postmortem" / "sample-postmortem.md").read_text()
        self.assertEqual(us.check_postmortem(text), [])

    def test_postmortem_missing_root_causes_fails(self):
        text = (WORKBENCH / "fixtures" / "postmortem" / "sample-postmortem.md").read_text()
        problems = us.check_postmortem(text.replace("## Root causes", "## Causes"))
        self.assertIn("missing section: root causes", problems)

    def test_postmortem_must_open_with_verdict(self):
        problems = us.check_postmortem("# T\n\n## Lessons\nx\n")
        self.assertIn("first section must be the executive verdict", problems)

    def test_workflow_writes_postmortem_itself(self):
        text = (WORKBENCH / ".claude" / "workflows" / "workbench-health.md").read_text()
        self.assertIn("scripts/usage_story.py check-postmortem", text)
        self.assertIn("I do not draft it", text)
        self.assertIn("no postmortem this month", text)

    def test_workflow_points_at_script_and_dashboard(self):
        text = (WORKBENCH / ".claude" / "workflows" / "workbench-health.md").read_text()
        self.assertIn("scripts/usage_story.py data", text)
        self.assertIn("scripts/usage_story.py check", text)
        self.assertIn("AI cost dashboard", text)
        self.assertIn("reference/links.csv", text)
        self.assertIn("price-table estimate", text)
        self.assertIn("not committed", text)
        self.assertNotIn("person=", text)


if __name__ == "__main__":
    unittest.main()
