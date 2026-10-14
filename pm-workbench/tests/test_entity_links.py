"""Local entity links: explicit rows, inferred proposals, no tracker writes."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import entity_links  # noqa: E402
import workspace_layout  # noqa: E402

INIT_HEADER = (
    "id,name,stage,prd,prototype,experiment,launch,related_okr,"
    "related_decisions,related_risks,last_updated,notes"
)


def _initiatives(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class EntityLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "registers").mkdir()
        (self.root / "state").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_initiatives(self):
        path = self.root / "registers" / "initiatives.csv"
        path.write_text(
            INIT_HEADER
            + "\n"
            + "INIT-001,Bulk export history,building,,,,,,,,2026-10-01,Existing note\n"
            + "INIT-002,Other slice,discovery,,,,,,,,2026-10-01,\n",
            encoding="utf-8",
        )
        return path

    def test_explicit_key_is_tier_1_and_tracker_stays_empty(self):
        proposals = entity_links.build_proposals(
            prefixes=["ABC"],
            pairs=[],
            commits=[
                {
                    "repo": "repos/app",
                    "sha": "abcdef1234567890",
                    "keys": ["ABC-1"],
                }
            ],
            first_seen="2026-10-14",
        )
        self.assertEqual(proposals["register_writes"], [])
        self.assertEqual(proposals["tracker_writes"], [])
        self.assertEqual(len(proposals["explicit"]), 1)
        row = proposals["explicit"][0]
        self.assertEqual(row["status"], "confirmed")
        self.assertEqual(row["type"], "commit-ticket")
        self.assertEqual(row["to"], "ABC-1")
        self.assertTrue(row["from"].startswith("repos/app@"))
        entity_links.upsert_links(self.root, proposals["explicit"])
        stored = entity_links.read_links(self.root)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["status"], "confirmed")
        self.assertEqual(entity_links.external_tracker_writes(stored, approved=False), [])
        source = Path(entity_links.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("atlassian", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)

    def test_inferred_pair_stays_proposed_until_approved(self):
        proposals = entity_links.build_proposals(
            prefixes=["ABC", "XYZ"],
            pairs=[("ABC", "XYZ")],
            tickets=[{"key": "ABC-1", "status": "To Do", "parent": "ABC-9", "links": []}],
            first_seen="2026-10-14",
        )
        inferred = [row for row in proposals["inferred"] if row["type"] == "paired-tickets"]
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0]["status"], "proposed")
        self.assertEqual(inferred[0]["to"], "XYZ:?")
        self.assertEqual(inferred[0]["confidence"], "low")
        explicit = [row for row in proposals["explicit"] if row["type"] == "ticket-epic"]
        self.assertEqual(explicit[0]["to"], "ABC-9")
        self.assertEqual(explicit[0]["status"], "confirmed")
        entity_links.upsert_links(self.root, proposals["explicit"] + proposals["inferred"])
        self.assertEqual(
            entity_links.confirm_proposed(
                self.root, [("ABC-1", "XYZ:?", "paired-tickets")], approved=False
            ),
            [],
        )
        still = entity_links.read_links(self.root)
        pair = next(row for row in still if row["type"] == "paired-tickets")
        self.assertEqual(pair["status"], "proposed")
        changed = entity_links.confirm_proposed(
            self.root, [("ABC-1", "XYZ:?", "paired-tickets")], approved=True
        )
        self.assertEqual(changed[0]["status"], "confirmed")
        approved_payloads = entity_links.external_tracker_writes(
            entity_links.read_links(self.root), approved=True
        )
        self.assertTrue(any(item["type"] == "ticket-epic" for item in approved_payloads))
        self.assertFalse(any(item["to"].endswith(":?") for item in approved_payloads))

    def test_confirmed_link_updates_initiative_in_place(self):
        path = self._write_initiatives()
        proposals = entity_links.build_proposals(
            prefixes=["ABC"],
            pairs=[],
            tickets=[
                {
                    "key": "ABC-4",
                    "status": "In Progress",
                    "parent": "ABC-1",
                    "summary": "Bulk export history filters",
                }
            ],
            initiatives=_initiatives(path),
            first_seen="2026-10-14",
        )
        named = [
            row
            for row in proposals["inferred"]
            if row["type"] == "ticket-initiative" and row["to"] == "INIT-001"
        ]
        self.assertEqual(len(named), 1)
        self.assertEqual(named[0]["status"], "proposed")
        entity_links.upsert_links(
            self.root,
            [
                {
                    "from": "ABC-4",
                    "to": "INIT-002",
                    "type": "ticket-initiative",
                    "source": "comment:ABC-4",
                    "confidence": "high",
                    "status": "confirmed",
                    "first_seen": "2026-10-14",
                },
                named[0],
            ],
        )
        before = _initiatives(path)
        updated = entity_links.apply_confirmed_to_initiatives(self.root, today="2026-10-14")
        self.assertEqual(updated, ["INIT-002"])
        after = _initiatives(path)
        self.assertEqual([row["id"] for row in after], ["INIT-001", "INIT-002"])
        self.assertEqual(after[0]["notes"], before[0]["notes"])
        self.assertEqual(after[0]["stage"], "building")
        self.assertEqual(after[1]["stage"], "discovery")
        self.assertIn("links: ABC-4 (ticket-initiative)", after[1]["notes"])
        self.assertEqual(after[1]["last_updated"], "2026-10-14")
        again = entity_links.apply_confirmed_to_initiatives(self.root, today="2026-10-15")
        self.assertEqual(again, [])

    def test_comment_text_proposes_candidates_without_register_writes(self):
        comments = [
            {
                "ticket": "ABC-1",
                "body": "DEC-004: we decided to keep the filter.",
                "created": "2026-10-01",
            },
            {
                "ticket": "ABC-2",
                "body": "This is blocked on a review with no named ticket.",
                "created": "2026-10-02",
            },
            {
                "ticket": "ABC-3",
                "body": "Risk: the date might slip if the review stays open.",
                "created": "2026-10-03",
            },
        ]
        proposals = entity_links.build_proposals(
            prefixes=["ABC"],
            pairs=[],
            tickets=[
                {"key": "ABC-1", "parent": "ABC-9"},
                {"key": "ABC-2", "parent": "ABC-9"},
                {"key": "ABC-3", "parent": "ABC-9"},
            ],
            comments=comments,
            first_seen="2026-10-14",
        )
        kinds = {item["kind"] for item in proposals["candidates"]}
        self.assertEqual(kinds, {"decision", "blocker", "risk"})
        self.assertTrue(all(item["auto_written"] is False for item in proposals["candidates"]))
        decision = next(item for item in proposals["candidates"] if item["kind"] == "decision")
        self.assertEqual(decision["cited"], ["DEC-004"])
        links = [
            row
            for row in proposals["explicit"]
            if row["type"] == "ticket-decision" and row["to"] == "DEC-004"
        ]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["status"], "confirmed")
        self.assertEqual(proposals["register_writes"], [])
        self.assertEqual(entity_links.external_tracker_writes(proposals["explicit"], approved=False), [])

    def test_seed_writes_the_entity_link_header(self):
        written = workspace_layout.seed_empty_registers(self.root)
        self.assertIn("state/entity-links.csv", written)
        header = (self.root / "state" / "entity-links.csv").read_text(encoding="utf-8")
        self.assertEqual(header, "from,to,type,source,confidence,status,first_seen\n")


if __name__ == "__main__":
    unittest.main()
