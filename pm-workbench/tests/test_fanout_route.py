"""Typed fan-out routes and analysis-index staleness."""
import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import analysis_index  # noqa: E402
import context_preflight  # noqa: E402
import fanout_route  # noqa: E402


class FanoutRouteTests(unittest.TestCase):
    def test_each_type_maps_and_no_surface_is_orphaned(self):
        expected = {
            "decision": {1, 3, 5},
            "commitment": {1},
            "risk": {1, 5},
            "evidence": {2, 3, 7},
            "metric": {12},
            "competitor": {3, 8},
            "term": {11},
            "durable-product-fact": {3, 6},
            "assumption": {4},
            "follow-up": {9, 10},
            "analysis": {13},
            "external-grounding": {14},
            "strategy-frame": {3, 4, 5, 6, 12, 15},
            "semantic-definition": {3, 4, 6, 13, 15},
            "stakeholder-stance": {15},
            "visual": {16},
        }
        self.assertEqual(set(fanout_route.ROUTES), set(expected))
        for key, surfaces in expected.items():
            self.assertEqual(set(fanout_route.routes_for([key])[key]), surfaces)
        self.assertEqual(fanout_route.orphan_surfaces(), [])
        self.assertEqual(fanout_route.check(), [])
        self.assertEqual(
            set(fanout_route.surfaces_for(["durable product fact"])),
            {3, 6},
        )

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(KeyError):
            fanout_route.routes_for(["vibes"])

    def test_fanout_doc_drops_the_na_list_and_keeps_required_phrases(self):
        text = (WORKBENCH / ".claude/workflows/_fan-out.md").read_text(encoding="utf-8")
        self.assertNotIn("Surfaces checked N/A", text)
        self.assertIn("learning/entities/", text)
        self.assertIn("state/web-search/", text)
        self.assertIn("stale_since", text)
        self.assertIn("Surface budget", text)
        self.assertIn("Rule 23", text)
        self.assertIn("Rule 24", text)
        self.assertIn("state/source-index.csv", text)
        self.assertIn("state/image-catalog.csv", text)
        self.assertIn("proposal only", text.lower())
        self.assertIn("business-level", text)
        for key in fanout_route.ROUTES:
            self.assertIn(key, text)

    def test_strategy_frame_surface_5_is_proposal_only_in_doc(self):
        text = (WORKBENCH / ".claude/workflows/_fan-out.md").read_text(encoding="utf-8")
        # Surface 5 for strategy-frame must be proposal-only (Tier 3).
        self.assertRegex(
            text,
            r"strategy-frame[\s\S]{0,400}proposal only",
            msg="strategy-frame must declare surface 5 proposal-only",
        )
        self.assertIn(15, fanout_route.SURFACES)
        self.assertEqual(fanout_route.orphan_surfaces(), [])


class StalenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()
        path = self.root / "state" / "analysis-index.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(
                [
                    "topic_key",
                    "initiative_ids",
                    "kind",
                    "path",
                    "as_of_date",
                    "one_line",
                    "primary_sources",
                    "source_workflow",
                    "indexed_date",
                ]
            )
            writer.writerow(
                [
                    "export",
                    "INIT-001",
                    "brief",
                    "outputs/prds/export.md",
                    "2026-09-01",
                    "Export brief",
                    "archive/meetings/kickoff.md",
                    "prd-package",
                    "2026-09-01",
                ]
            )
            writer.writerow(
                [
                    "events",
                    "INIT-009",
                    "instrumentation",
                    "outputs/daily/events.md",
                    "2026-09-01",
                    "Events",
                    "repos/app@abc",
                    "code-dive",
                    "2026-09-01",
                ]
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_mark_stale_sets_earliest_date_and_living_filter(self):
        flagged = analysis_index.mark_stale(
            self.root,
            initiative_ids="INIT-001",
            reason="new decision",
            since="2026-10-14",
            except_path="outputs/daily/today.md",
        )
        self.assertEqual(flagged, ["outputs/prds/export.md"])
        again = analysis_index.mark_stale(
            self.root,
            initiative_ids="INIT-001",
            reason="later fact",
            since="2026-10-20",
        )
        self.assertEqual(again, ["outputs/prds/export.md"])
        rows = {row["path"]: row for row in analysis_index.read_rows(self.root)}
        self.assertEqual(rows["outputs/prds/export.md"]["stale_since"], "2026-10-14")
        self.assertEqual(rows["outputs/prds/export.md"]["stale_reason"], "new decision")
        self.assertEqual(rows["outputs/daily/events.md"]["stale_since"], "")
        living = analysis_index.stale_rows(self.root, living_only=True)
        self.assertEqual([row["path"] for row in living], ["outputs/prds/export.md"])

        analysis_index.mark_stale(
            self.root,
            primary_sources="archive/meetings/kickoff.md",
            since="2026-10-01",
            reason="earlier source touch",
        )
        rows = {row["path"]: row for row in analysis_index.read_rows(self.root)}
        self.assertEqual(rows["outputs/prds/export.md"]["stale_since"], "2026-10-01")

        wrote = analysis_index.append_row(
            self.root,
            topic_key="export",
            path="outputs/prds/export.md",
            kind="brief",
            as_of_date="2026-10-14",
            one_line="Export brief refreshed",
            refresh=True,
        )
        self.assertTrue(wrote)
        rows = {row["path"]: row for row in analysis_index.read_rows(self.root)}
        self.assertEqual(rows["outputs/prds/export.md"]["stale_since"], "")
        self.assertEqual(rows["outputs/prds/export.md"]["as_of_date"], "2026-10-14")

    def test_preflight_returns_stale_flag_and_scans_strategy_roadmap_drafts(self):
        analysis_index.mark_stale(
            self.root,
            initiative_ids="INIT-001",
            since="2026-10-14",
            reason="touched",
        )
        strategy = self.root / "outputs" / "strategy"
        strategy.mkdir(parents=True)
        (strategy / "2026-10-01-export-strategy.md").write_text(
            "# Export strategy\n\nINIT-001 still open.\n",
            encoding="utf-8",
        )
        roadmap = self.root / "roadmap"
        roadmap.mkdir()
        (roadmap / "export.md").write_text("# Export roadmap\n", encoding="utf-8")
        drafts = self.root / "drafts"
        drafts.mkdir()
        (drafts / "export-notes.md").write_text("# Export notes\n\nNot evidence.\n", encoding="utf-8")

        marker = context_preflight.run_preflight(self.root, "export INIT-001")
        by_path = {hit["path"]: hit for hit in marker["hits"]}
        self.assertIn("outputs/prds/export.md", by_path)
        self.assertEqual(by_path["outputs/prds/export.md"]["stale_since"], "2026-10-14")
        self.assertIn("outputs/strategy/2026-10-01-export-strategy.md", by_path)
        self.assertIn("roadmap/export.md", by_path)
        self.assertIn("drafts/export-notes.md", by_path)
        self.assertFalse(by_path["drafts/export-notes.md"]["evidence"])
        self.assertTrue(by_path["drafts/export-notes.md"]["derived"])
        self.assertEqual(marker["recommendation"], "reuse_and_refresh")
        self.assertTrue(any("stale_since" in signal for signal in marker["newer_signals"]))


class DependencyHeaderTests(unittest.TestCase):
    def test_declared_ids_exist_in_the_manifest(self):
        import context_health

        ids = {row["id"] for row in context_health.load_manifest(WORKBENCH)}
        workflows = WORKBENCH / ".claude" / "workflows"
        declared = 0
        for path in workflows.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            declared_lines = [
                ln for ln in text.splitlines() if ln.startswith("Context dependencies:")
            ]
            if not declared_lines:
                continue
            declared += 1
            line = declared_lines[0]
            body = line.split(":", 1)[1]
            for token in re.findall(r"[a-z][a-z0-9-]*", body):
                if token in {"soft", "hard", "none"}:
                    continue
                self.assertIn(token, ids, f"{path.name} uses unknown id {token}")
        self.assertGreaterEqual(declared, 8)
        protocol = (workflows / "_protocol.md").read_text(encoding="utf-8")
        self.assertIn("Context dependencies", protocol)
        self.assertIn("derived, not stated priorities", protocol)
        brief = (workflows / "daily-brief.md").read_text(encoding="utf-8")
        self.assertIn("context_health.py", brief)
        self.assertIn("stale_since", brief)
        setup = (workflows / "context-setup.md").read_text(encoding="utf-8")
        self.assertIn("chat_harvest.py", setup)
        self.assertIn("memory_harvest.py", setup)
        self.assertIn("CLAUDE.local.md", setup)


if __name__ == "__main__":
    unittest.main()
