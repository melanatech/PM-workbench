#!/usr/bin/env python3
"""Synthetic SQLite + dashboard CSV tests for scripts/import_cursor_usage.py."""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import import_cursor_usage as icu  # noqa: E402

SECRET = "SECRET_MESSAGE_DO_NOT_STORE_9f3c"


def _db_with(rows: list[tuple[str, str]], headers: list[tuple] | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="pmwb-cursor-"))
    path = tmp / "state.vscdb"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)")
    conn.executemany("INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)", rows)
    if headers is not None:
        conn.execute(
            "CREATE TABLE composerHeaders ("
            "composerId TEXT, workspaceId TEXT, value TEXT)"
        )
        conn.executemany(
            "INSERT INTO composerHeaders (composerId, workspaceId, value) VALUES (?, ?, ?)",
            headers,
        )
    conn.commit()
    conn.close()
    return path


def _composer(cid: str, **overrides) -> str:
    data = {
        "composerId": cid,
        "createdAt": 1760000000000,  # 2025-10-09-ish; tests override
        "name": "Daily brief",
        "modelConfig": {"modelName": "composer-2-fast"},
        "subagentComposerIds": [],
        "text": SECRET,
    }
    data.update(overrides)
    return json.dumps(data)


def _bubble(role: str, created: str, text: str = SECRET) -> str:
    type_value = 1 if role == "user" else 2
    return json.dumps({
        "type": type_value,
        "createdAt": created,
        "text": text,
        "tokenCount": {"inputTokens": 0, "outputTokens": 0},
    })


class ReadOnlyTests(unittest.TestCase):
    def test_uri_is_readonly_immutable(self):
        path = Path("/tmp/cursor state.vscdb")
        uri = icu.sqlite_uri(path)
        self.assertIn("mode=ro", uri)
        self.assertIn("immutable=1", uri)
        self.assertNotIn(" ", uri.split("?", 1)[0])

    def test_open_rejects_writes(self):
        db = _db_with([("composerData:abc", _composer("abc"))])
        self.addCleanup(lambda: __import__("shutil").rmtree(db.parent, ignore_errors=True))
        conn = icu.open_readonly(db)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("INSERT INTO cursorDiskKV (key, value) VALUES ('x', 'y')")
        conn.close()


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.cid = "11111111-1111-1111-1111-111111111111"
        self.other = "22222222-2222-2222-2222-222222222222"
        created_ms = int(icu._parse_time("2025-10-09T08:00:00Z").timestamp() * 1000)
        header_value = json.dumps({
            "composerId": self.cid,
            "workspaceIdentifier": {
                "id": "ws",
                "uri": {"fsPath": "/Users/someone/pm-live", "path": "/Users/someone/pm-live"},
            },
        })
        self.db = _db_with(
            [
                (
                    f"composerData:{self.cid}",
                    _composer(
                        self.cid,
                        createdAt=created_ms,
                        name="/brief daily-brief",
                        modelConfig={"modelName": "composer-2-fast"},
                        subagentComposerIds=["sub-a", "sub-b"],
                        workspaceIdentifier=None,
                    ),
                ),
                (
                    f"composerData:{self.other}",
                    _composer(
                        self.other,
                        createdAt=created_ms + 3_600_000,
                        name="what did we decide about INIT-033?",
                        modelConfig={"modelName": "grok-4.5"},
                        workspaceIdentifier={
                            "uri": {"fsPath": "/Users/someone/notes"}
                        },
                        subagentComposerIds=[],
                    ),
                ),
                ("composerData:bad", "{not json"),
                (
                    f"bubbleId:{self.cid}:b1",
                    _bubble("user", "2025-10-09T08:00:00.000Z", "please /brief daily-brief now"),
                ),
                (
                    f"bubbleId:{self.cid}:b2",
                    _bubble("assistant", "2025-10-09T08:05:00.000Z", SECRET),
                ),
                (
                    f"bubbleId:{self.cid}:b3",
                    _bubble("user", "2025-10-09T08:10:00.000Z", "later question"),
                ),
                (f"bubbleId:{self.other}:b4", _bubble("user", "2025-10-09T09:00:00.000Z")),
                ("bubbleId:missing-composer:b5", _bubble("user", "2025-10-09T09:30:00.000Z")),
                (f"bubbleId:{self.cid}:bad", "{still not json"),
            ],
            headers=[(self.cid, "empty-window", header_value)],
        )
        self.addCleanup(lambda: __import__("shutil").rmtree(self.db.parent, ignore_errors=True))

    def test_counts_category_and_no_message_leak(self):
        root = self.db.parent / "live"
        stats = icu.run_import(db_path=self.db, root=root)
        self.assertEqual(stats["composers_seen"], 3)
        self.assertEqual(stats["composers_imported"], 2)
        self.assertEqual(stats["composers_skipped"], 1)
        self.assertGreaterEqual(stats["bubbles_skipped"], 2)

        path = root / "state" / "cursor-activity.csv"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(SECRET, text)
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 2)
        by_id = {r["id"]: r for r in rows}
        first = by_id[self.cid]
        self.assertEqual(first["user_msgs"], "2")
        self.assertEqual(first["assistant_msgs"], "1")
        self.assertEqual(first["subagent_count"], "2")
        self.assertEqual(first["selected_model"], "composer-2-fast")
        self.assertEqual(first["workspace"], "/Users/someone/pm-live")
        self.assertEqual(first["kit_related"], "yes")
        self.assertEqual(first["category"], "workflow:daily-brief")
        self.assertEqual(first["harness"], "cursor")
        self.assertEqual(first["surface"], "cursor-agent")
        self.assertEqual(first["title"], "/brief daily-brief")
        self.assertTrue(first["created"])
        self.assertEqual(first["last_message"], "2025-10-09T08:10:00Z")
        second = by_id[self.other]
        self.assertEqual(second["kit_related"], "no")
        self.assertEqual(second["category"], "lookup")
        self.assertEqual(second["workspace"], "/Users/someone/notes")


class UsageJoinTests(unittest.TestCase):
    def test_timestamp_and_model_join(self):
        wide = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        tight = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        db = _db_with([
            (
                f"composerData:{wide}",
                _composer(
                    wide,
                    createdAt=1_759_300_800_000,  # overridden by bubbles' last + createdAt
                    name="wide",
                    modelConfig={"modelName": "composer-2-fast"},
                ),
            ),
            (
                f"composerData:{tight}",
                _composer(
                    tight,
                    name="tight",
                    modelConfig={"modelName": "composer-2-fast"},
                ),
            ),
        ])
        self.addCleanup(lambda: __import__("shutil").rmtree(db.parent, ignore_errors=True))
        # Set created/last via bubbles and createdAt ms that _parse_time understands.
        # 2026-10-01T10:00:00Z = 1759312800? Let the importer read createdAt from composer
        # and last_message from bubbles. Patch composer createdAt to known ms.
        start_ms = 1_759_312_800_000  # computed below in assertion via ISO from script
        # Use explicit ISO by writing createdAt as ms for 2026-10-01T10:00:00Z
        # and 10:15. Calculate with the same helper.
        wide_start = icu._parse_time("2026-10-01T10:00:00Z")
        tight_start = icu._parse_time("2026-10-01T10:15:00Z")
        assert wide_start and tight_start
        wide_ms = int(wide_start.timestamp() * 1000)
        tight_ms = int(tight_start.timestamp() * 1000)
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM cursorDiskKV")
        conn.executemany(
            "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)",
            [
                (
                    f"composerData:{wide}",
                    _composer(
                        wide,
                        createdAt=wide_ms,
                        name="wide window",
                        modelConfig={"modelName": "composer-2-fast"},
                    ),
                ),
                (
                    f"composerData:{tight}",
                    _composer(
                        tight,
                        createdAt=tight_ms,
                        name="tight window",
                        modelConfig={"modelName": "composer-2-fast"},
                    ),
                ),
                (
                    f"bubbleId:{wide}:u",
                    _bubble("user", "2026-10-01T10:00:00.000Z", "hello wide"),
                ),
                (
                    f"bubbleId:{wide}:a",
                    _bubble("assistant", "2026-10-01T12:00:00.000Z", SECRET),
                ),
                (
                    f"bubbleId:{tight}:u",
                    _bubble("user", "2026-10-01T10:15:00.000Z", "hello tight"),
                ),
                (
                    f"bubbleId:{tight}:a",
                    _bubble("assistant", "2026-10-01T10:45:00.000Z", SECRET),
                ),
            ],
        )
        conn.commit()
        conn.close()

        usage = db.parent / "usage.csv"
        with usage.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow([
                "Date", "Kind", "Model", "Input Tokens", "Cache Write",
                "Cache Read", "Output Tokens", "Cost",
            ])
            w.writerow([
                "2026-10-01T10:30:00Z", "Included", "composer-2-fast",
                "100", "10", "40", "20", "$0.50",
            ])
            w.writerow([
                "2026-10-01T10:30:00Z", "Included", "other-model",
                "1", "0", "0", "1", "0.01",
            ])
            w.writerow([
                "2026-10-03T10:30:00Z", "Included", "composer-2-fast",
                "1", "0", "0", "1", "0.01",
            ])
            w.writerow(["not-a-date", "Included", "composer-2-fast", "1", "", "", "1", ""])

        root = db.parent / "live"
        stats = icu.run_import(
            db_path=db,
            root=root,
            usage_csv=usage,
            join_minutes=120,
        )
        self.assertEqual(stats["usage_seen"], 4)
        self.assertEqual(stats["usage_imported"], 3)
        self.assertEqual(stats["usage_skipped"], 1)
        self.assertEqual(stats["usage_matched"], 1)
        self.assertEqual(stats["usage_unmatched"], 2)
        with (root / "state" / "cursor-usage.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["conversation_id"], tight)
        self.assertEqual(rows[0]["input_tokens"], "100")
        self.assertEqual(rows[0]["cache_write_tokens"], "10")
        self.assertEqual(rows[0]["cache_read_tokens"], "40")
        self.assertEqual(rows[0]["output_tokens"], "20")
        self.assertEqual(rows[0]["cost"], "0.5")
        self.assertEqual(rows[0]["harness"], "cursor")
        self.assertEqual(rows[1]["conversation_id"], "")
        self.assertEqual(rows[2]["conversation_id"], "")
        blob = (root / "state" / "cursor-usage.csv").read_text(encoding="utf-8")
        blob += (root / "state" / "cursor-activity.csv").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("hello tight", blob)
        self.assertNotIn("hello wide", blob)


class HelperTests(unittest.TestCase):
    def test_role_and_headers(self):
        self.assertEqual(icu.bubble_role(1), "user")
        self.assertEqual(icu.bubble_role(2), "assistant")
        self.assertEqual(icu.bubble_role("assistant"), "assistant")
        self.assertIsNone(icu.bubble_role(None))
        self.assertEqual(icu._header_field("Input (w/o Cache Write)"), "input_tokens")
        self.assertEqual(icu._header_field("Cache Read Tokens"), "cache_read_tokens")


if __name__ == "__main__":
    unittest.main()
