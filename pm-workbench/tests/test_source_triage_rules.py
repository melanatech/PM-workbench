"""Guardrail presence tests for source triage (text contracts)."""
from __future__ import annotations

import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
TRIAGE = (WORKBENCH / ".claude/workflows/_source-triage.md").read_text(encoding="utf-8")
FANOUT = (WORKBENCH / ".claude/workflows/_fan-out.md").read_text(encoding="utf-8")
PROCESS = (WORKBENCH / ".claude/workflows/process-inbox.md").read_text(encoding="utf-8")
CLOSEOUT = (WORKBENCH / ".claude/workflows/meeting-closeout.md").read_text(encoding="utf-8")
RECONCILE = (WORKBENCH / ".claude/workflows/context-reconcile.md").read_text(encoding="utf-8")
PREP = (WORKBENCH / ".claude/workflows/meeting-prep.md").read_text(encoding="utf-8")


class SourceTriageRulesTests(unittest.TestCase):
    def test_business_level_is_forbidden_skip_reason(self):
        self.assertIn("business-level", TRIAGE)
        self.assertIn("Forbidden", TRIAGE + FANOUT)
        self.assertIn("business-level", FANOUT)

    def test_engineering_keep_list_present(self):
        for phrase in (
            "merchant-visible behavior",
            "launch readiness",
            "instrumentation",
            "cost or capacity",
        ):
            self.assertIn(phrase, TRIAGE)
        self.assertIn("engineering keep-list", CLOSEOUT.lower())

    def test_initiatives_and_priorities_are_proposal_only(self):
        self.assertIn("INITIATIVE CANDIDATE", TRIAGE)
        self.assertIn("proposal only", TRIAGE.lower())
        self.assertIn("proposal only", FANOUT.lower())
        self.assertIn("Tier 3", FANOUT)

    def test_hold_and_promote_rules(self):
        self.assertIn("outcome: promote | index | hold | ignore | duplicate", TRIAGE)
        self.assertIn("second independent source", TRIAGE)
        self.assertIn("status=promoted", TRIAGE)
        self.assertIn("cross-source", PROCESS.lower())

    def test_exploratory_thinking_forbids_ev_and_owner_questions(self):
        self.assertIn("exploratory-thinking", TRIAGE)
        self.assertIn("No EV rows", TRIAGE)
        self.assertIn("No DEC / COM rows", TRIAGE)
        self.assertIn("no questions about owners or decisions", TRIAGE.lower())
        self.assertIn("exploratory-thinking", CLOSEOUT)

    def test_parked_marker_honored(self):
        self.assertIn("parked YYYY-MM-DD", TRIAGE)
        self.assertIn("parked", FANOUT.lower())
        self.assertIn("parked", RECONCILE.lower())

    def test_glossary_limited_to_acronyms(self):
        self.assertIn("acronyms and standing internal names", TRIAGE.lower())
        self.assertIn("Ordinary phrases", TRIAGE)
        self.assertIn("Ordinary phrases", FANOUT)

    def test_own_outputs_never_evidence(self):
        self.assertIn("derived-own", TRIAGE)
        self.assertIn("Never a source of evidence", TRIAGE)
        self.assertIn("is-own-output", PROCESS)

    def test_ai_summaries_cannot_confirm_alone(self):
        self.assertIn("ai-summary", TRIAGE)
        self.assertIn("cannot confirm", TRIAGE.lower())
        self.assertIn("primary", TRIAGE)

    def test_status_claims_needs_authority(self):
        self.assertIn("needs-authority", TRIAGE)
        self.assertIn("needs-authority", CLOSEOUT)
        self.assertIn("needs-authority", PROCESS)

    def test_redaction_before_profiling(self):
        self.assertIn("redacted before any durable write", TRIAGE.lower())
        self.assertIn("data profile", TRIAGE.lower())
        self.assertIn("redact", PROCESS.lower())

    def test_kit_feedback_goes_to_backlog(self):
        self.assertIn("kit-feedback", TRIAGE)
        self.assertIn("BACKLOG.md", TRIAGE)
        self.assertIn("Do **not** edit workflow text in the same run", TRIAGE)

    def test_partial_reads_listed(self):
        self.assertIn("unread", TRIAGE)
        self.assertIn("partly read", TRIAGE.lower())
        self.assertIn("unread", PROCESS.lower())

    def test_workflows_wire_triage(self):
        self.assertIn("_source-triage.md", PROCESS)
        self.assertIn("_source-triage.md", CLOSEOUT)
        self.assertIn("source_index.py", RECONCILE)
        self.assertIn("people.md", PREP)

    def test_image_catalog_required_after_vision(self):
        self.assertIn("image-catalog.csv", TRIAGE)
        self.assertIn("image_catalog.py", PROCESS)
        self.assertIn("images catalogued", PROCESS.lower())

    def test_ask_budget(self):
        self.assertIn("Ask budget", TRIAGE)
        self.assertIn("at most one batch", TRIAGE.lower())

    def test_lumenly_triage_fixture_present(self):
        expected = WORKBENCH / "fixtures/lumenly/triage/EXPECTED.md"
        self.assertTrue(expected.is_file())
        text = expected.read_text(encoding="utf-8")
        for needle in (
            "strategy-frame",
            "exploratory-thinking",
            "needs-authority",
            "derived-own",
            "INITIATIVE CANDIDATE",
            "ignore",
        ):
            self.assertIn(needle, text)
        meetings = WORKBENCH / "fixtures/lumenly/triage/meetings/2026-10-15-things-to-think-about.md"
        self.assertTrue(meetings.is_file())


if __name__ == "__main__":
    unittest.main()
