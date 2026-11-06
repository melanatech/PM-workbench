"""P0 draft gates: settled facts, requirements ledger, roadmap audience, output index."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))

import job_card  # noqa: E402
import output_index  # noqa: E402
import quiet_progress  # noqa: E402
import requirements_ledger  # noqa: E402
import roadmap_audience  # noqa: E402
import settled_facts  # noqa: E402


FACTS = """
## SF-001
status: active
scope: roadmap,insights
fact: Summary report shipped.
forbid: where did my deposit go
forbid: summary report
allow: shipped
allow: already
source: chat
"""

LEDGER = """
## RR-01
status: accepted
must_include: busiest selling times
note: first insight
## RR-02
status: removed
must_include: dropped phrase
"""


class SettledFactTests(unittest.TestCase):
    def test_reopen_blocks(self):
        facts = [f for f in settled_facts.parse_facts(FACTS) if f.status == "active"]
        text = "Now: build a where did my deposit go view"
        found = settled_facts.violations(text, "outputs/external/roadmap.html", facts)
        self.assertEqual(len(found), 1)

    def test_allow_window_passes(self):
        facts = [f for f in settled_facts.parse_facts(FACTS) if f.status == "active"]
        text = "where did my deposit go is already answered by the shipped summary report"
        self.assertEqual(settled_facts.violations(text, "outputs/external/roadmap.html", facts), [])

    def test_other_paths_skip_scope(self):
        facts = [f for f in settled_facts.parse_facts(FACTS) if f.status == "active"]
        text = "where did my deposit go"
        self.assertEqual(settled_facts.violations(text, "outputs/prds/note.md", facts), [])

    def test_example_status_ignored(self):
        text = "## SF-000\nstatus: example\nforbid: hello\n"
        self.assertEqual(settled_facts.parse_facts(text)[0].status, "example")


class LedgerTests(unittest.TestCase):
    def test_missing_accepted_row(self):
        rows = requirements_ledger.parse_ledger(LEDGER)
        accepted = [r for r in rows if r.status == "accepted"]
        self.assertEqual(requirements_ledger.missing("a roadmap with no insight", accepted), ["RR-01 missing 'busiest selling times' — first insight"])

    def test_removed_row_not_required(self):
        rows = [r for r in requirements_ledger.parse_ledger(LEDGER) if r.status == "accepted"]
        self.assertEqual(len(rows), 1)

    def test_family_from_filename(self):
        self.assertEqual(requirements_ledger.family_for("outputs/external/2026-10-16-roadmap.html"), "roadmap")
        self.assertIsNone(requirements_ledger.family_for("outputs/external/notes.md"))
        self.assertIsNone(requirements_ledger.family_for("outputs/todo-drafts/TODO-016-voiceit-roadmap.md"))
        self.assertIsNone(requirements_ledger.family_for("outputs/external/slack-roadmap-comms.md"))

    def test_check_file_reads_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state" / "requirements").mkdir(parents=True)
            (root / "state" / "requirements" / "roadmap.md").write_text(LEDGER, encoding="utf-8")
            draft = root / "outputs" / "external"
            draft.mkdir(parents=True)
            path = draft / "roadmap.md"
            path.write_text("no insight here", encoding="utf-8")
            found = requirements_ledger.check_file(root, path, "outputs/external/roadmap.md")
            self.assertTrue(any("RR-01" in line for line in found))
            path.write_text("busiest selling times stays first", encoding="utf-8")
            self.assertEqual(requirements_ledger.check_file(root, path, "outputs/external/roadmap.md"), [])


class AudienceTests(unittest.TestCase):
    def test_changelog_and_mix(self):
        text = """
        <h2>What's changed</h2>
        <h2>Now</h2>
        <ul>
          <li><b>Busiest selling times</b> first insight</li>
          <li><b>Follow-up</b> PROJ-1 PROJ-2 PROJ-3 parity fixes after release</li>
        </ul>
        <h2>Next</h2>
        """
        found = roadmap_audience.findings_for(text)
        self.assertTrue(any(line.startswith("changelog_voice") for line in found))
        self.assertTrue(any(line.startswith("granularity_mix") for line in found))

    def test_crowded_now_fails_even_if_it_says_first(self):
        items = "\n".join(f"<li><b>Item {i}</b> key TBD committed</li>" for i in range(6))
        text = f"<h2>Now</h2><p>Busiest stays first.</p><ul>{items}</ul><h2>Next</h2>"
        found = roadmap_audience.findings_for(text)
        self.assertTrue(any(line.startswith("now_overloaded") for line in found))

    def test_clean_board_passes(self):
        text = """
        <h2>Now</h2>
        <p>Order is priority. Busiest selling times stays first.</p>
        <ul>
          <li><b>Busiest selling times</b> heat map</li>
          <li><b>Inventory report</b> IDEA-1 committed rebuild</li>
        </ul>
        <h2>Next</h2>
        <ul><li><b>Dashboard</b></li></ul>
        """
        self.assertEqual(roadmap_audience.findings_for(text), [])

    def test_only_external_roadmap_paths(self):
        self.assertFalse(roadmap_audience.is_external_roadmap("outputs/strategy/roadmap-critique.md"))
        self.assertTrue(roadmap_audience.is_external_roadmap("outputs/external/roadmap.html"))


class OutputIndexTests(unittest.TestCase):
    def test_many_links_without_heading(self):
        text = "\n".join(f"[a](outputs/external/{i}.md)" for i in range(4))
        self.assertEqual(len(output_index.reply_missing_index(text)), 4)

    def test_heading_satisfies(self):
        text = "## Output index\n" + "\n".join(f"[a](outputs/external/{i}.md)" for i in range(4))
        self.assertEqual(output_index.reply_missing_index(text), [])

    def test_few_links_skip(self):
        text = "[a](outputs/external/one.md)"
        self.assertEqual(output_index.reply_missing_index(text), [])

    def test_render_heading(self):
        rendered = output_index.render(["outputs/external/a.md"])
        self.assertIn("## Output index", rendered)
        self.assertIn("outputs/external/a.md", rendered)


CARD = """
enforce: on
job: Share a Q4 roadmap
audience: leadership
due: 2026-10-16
stop: No stream that is not listed
streams: roadmap, release notes
"""


class JobCardTests(unittest.TestCase):
    def test_missing_card_does_not_block_writes(self):
        self.assertEqual(job_card.stream_block("outputs/external/experiments.md", None), [])

    def test_outside_stream_blocks(self):
        card = job_card.parse_card(CARD)
        found = job_card.stream_block("outputs/external/experiment-plan.md", card)
        self.assertEqual(len(found), 1)

    def test_matching_stream_passes(self):
        card = job_card.parse_card(CARD)
        self.assertEqual(job_card.stream_block("outputs/external/2026-10-16-roadmap.html", card), [])
        self.assertEqual(job_card.stream_block("outputs/external/release-notes.md", card), [])

    def test_check_requires_due(self):
        card = job_card.parse_card("enforce: on\njob: x\naudience: y\nstop: z\nstreams: roadmap\n")
        self.assertTrue(any("due" in line for line in job_card.check_card(card)))


class QuietProgressTests(unittest.TestCase):
    def test_play_by_play_is_chatter(self):
        text = "The agent finished. Another is still running on a timer."
        self.assertGreaterEqual(len(quiet_progress.chatter_hits(text)), 2)

    def test_batch_line_is_quiet(self):
        self.assertEqual(quiet_progress.chatter_hits("Batch: 2 of 5 on disk."), [])

    def test_output_index_is_quiet(self):
        text = "## Output index\nThe agent finished earlier.\nstill running was the old problem."
        self.assertEqual(quiet_progress.chatter_hits(text), [])


if __name__ == "__main__":
    unittest.main()
