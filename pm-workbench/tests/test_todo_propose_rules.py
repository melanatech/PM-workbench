"""Guardrail: to-do proposals are actions only — not decisions/confirmations/open questions."""
from __future__ import annotations

import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
WORKER = (WORKBENCH / ".claude/agents/todo-worker.md").read_text(encoding="utf-8")
TODO_CMD = (WORKBENCH / ".claude/commands/todo.md").read_text(encoding="utf-8")
PROCESS = (WORKBENCH / ".claude/workflows/process-inbox.md").read_text(encoding="utf-8")
CLOSEOUT = (WORKBENCH / ".claude/workflows/meeting-closeout.md").read_text(encoding="utf-8")
RECONCILE = (WORKBENCH / ".claude/workflows/context-reconcile.md").read_text(encoding="utf-8")
FANOUT = (WORKBENCH / ".claude/workflows/_fan-out.md").read_text(encoding="utf-8")
QUICK = (WORKBENCH / ".claude/commands/quick-close.md").read_text(encoding="utf-8")
CONNECTIONS = (WORKBENCH / "CONNECTIONS.md").read_text(encoding="utf-8")


class TodoProposeRulesTests(unittest.TestCase):
    def test_worker_propose_is_actions_only(self):
        self.assertIn("Action test", WORKER)
        self.assertIn("decisions, confirmations, and open questions", WORKER.lower())
        self.assertNotIn("phrase it as confirm", WORKER.lower())
        self.assertIn("parked YYYY-MM-DD", WORKER)
        self.assertIn("assumptions-and-open-questions.md", WORKER)

    def test_worker_forbids_confirm_decide_candidates(self):
        self.assertIn('"decide…"', WORKER)
        self.assertIn('"confirm…"', WORKER)
        self.assertIn("confirm/decide", WORKER)

    def test_todo_command_states_action_filter(self):
        self.assertIn("action filter", TODO_CMD.lower())
        self.assertIn("NOT a decision or confirmation", TODO_CMD)
        self.assertIn("todo-worker", TODO_CMD)

    def test_capture_workflows_share_filter(self):
        for text, name in (
            (PROCESS, "process-inbox"),
            (CLOSEOUT, "meeting-closeout"),
            (RECONCILE, "context-reconcile"),
        ):
            with self.subTest(workflow=name):
                self.assertIn("actions only", text.lower(), msg=name)
                self.assertIn("todo-worker", text)

    def test_reconcile_marks_decision_skips(self):
        self.assertIn("skip (decision or open question — not a to-do)", RECONCILE)

    def test_strategy_refresh_inputs_not_separate_todos(self):
        self.assertIn("strategy-refresh", WORKER)
        self.assertIn("next consumer", WORKER.lower())

    def test_pm_owned_commitment_twins_a_todo(self):
        for text, name in (
            (CLOSEOUT, "meeting-closeout"),
            (PROCESS, "process-inbox"),
            (RECONCILE, "context-reconcile"),
            (FANOUT, "_fan-out"),
            (QUICK, "quick-close"),
            (TODO_CMD, "todo"),
            (CONNECTIONS, "CONNECTIONS"),
        ):
            with self.subTest(doc=name):
                self.assertIn("ensure-from-commitment", text, msg=name)
        self.assertIn("origin=commitment", FANOUT)
        self.assertIn("ensure-from-commitment", WORKER)


if __name__ == "__main__":
    unittest.main()
