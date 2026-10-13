#!/usr/bin/env python3
"""Tests for scripts/session_usage.py (L0–L2a; classify opt-in skipped without key)."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "session_usage.py"
sys.path.insert(0, str(WORKBENCH / "scripts"))
import session_usage  # noqa: E402


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


class ProjectsDiscoveryTests(unittest.TestCase):
    def test_discovers_live_and_workbench_encodings(self):
        from unittest.mock import patch

        tmp = Path(tempfile.mkdtemp(prefix="pmwb-proj-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        home = tmp / "home"
        live = tmp / "pm-live"
        kit = tmp / "PM-workbench"
        live.mkdir()
        kit.mkdir()
        home_claude = home / ".claude" / "projects"
        enc_live = home_claude / str(live.resolve()).replace("/", "-")
        enc_kit = home_claude / str(kit.resolve()).replace("/", "-")
        enc_live.mkdir(parents=True)
        enc_kit.mkdir(parents=True)

        with patch.object(session_usage.Path, "home", return_value=home):
            got = session_usage.default_projects_dirs(live)
        names = {p.name for p in got}
        self.assertIn(enc_live.name, names)
        self.assertIn(enc_kit.name, names)

    def test_backfill_scans_multiple_projects_dirs(self):
        tmp = Path(tempfile.mkdtemp(prefix="pmwb-multi-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        live = tmp / "live"
        live.mkdir()
        (live / "state").mkdir()
        p1 = tmp / "proj-a"
        p2 = tmp / "proj-b"
        p1.mkdir()
        p2.mkdir()
        for proj, sid, uid, aid in (
            (p1, "s1", "u1", "a1"),
            (p2, "s2", "u2", "a2"),
        ):
            _write_jsonl(
                proj / f"{sid}.jsonl",
                [
                    {
                        "type": "user",
                        "uuid": uid,
                        "timestamp": "2026-10-10T12:00:00.000Z",
                        "message": {
                            "role": "user",
                            "content": [{"type": "text", "text": "/brief daily-brief"}],
                        },
                    },
                    {
                        "type": "assistant",
                        "uuid": aid,
                        "timestamp": "2026-10-10T12:00:05.000Z",
                        "message": {
                            "role": "assistant",
                            "usage": {
                                "input_tokens": 1,
                                "output_tokens": 1,
                                "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 0,
                            },
                        },
                    },
                ],
            )
        n, files = session_usage.backfill(
            live, projects_dirs=[p1, p2], classify=False
        )
        self.assertEqual(files, 2)
        self.assertEqual(n, 2)


class ClassifyL2aTests(unittest.TestCase):
    def test_slash_workflow(self):
        cat, src = session_usage.classify_l2a("/brief daily-brief")
        self.assertEqual(cat, "workflow:daily-brief")
        self.assertEqual(src, "l2a")

    def test_explore_brief_coarse(self):
        cat, src = session_usage.classify_l2a("/discover explore-brief INIT-033")
        self.assertEqual(cat, "explore_brief")
        self.assertEqual(src, "l2a")

    def test_command_xml(self):
        text = (
            "<command-message>brief</command-message> "
            "<command-name>/brief</command-name> "
            "<command-args>daily-brief</command-args>"
        )
        cat, src = session_usage.classify_l2a(text)
        self.assertEqual(cat, "workflow:daily-brief")
        self.assertEqual(src, "l2a")

    def test_lookup_and_rework(self):
        cat, _ = session_usage.classify_l2a("what did we decide about INIT-033?")
        self.assertEqual(cat, "lookup")
        cat2, _ = session_usage.classify_l2a("you ignored the Oct 7 digest — fix that")
        self.assertEqual(cat2, "rework_correction")


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-usage-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "pm-live"
        self.live.mkdir()
        (self.live / "state").mkdir()
        self.projects = self.tmp / "projects" / "-Users-test-pm-live"
        self.projects.mkdir(parents=True)
        _write_jsonl(
            self.projects / "sess-aaa.jsonl",
            [
                {
                    "type": "user",
                    "uuid": "u1",
                    "timestamp": "2026-10-10T12:00:00.000Z",
                    "isMeta": False,
                    "isSidechain": False,
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "/discover code-dive reports"}],
                    },
                },
                {
                    "type": "assistant",
                    "uuid": "a1",
                    "timestamp": "2026-10-10T12:00:05.000Z",
                    "isSidechain": False,
                    "message": {
                        "role": "assistant",
                        "model": "claude-sonnet-4",
                        "content": [{"type": "text", "text": "Looking at the repo."}],
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_input_tokens": 1000,
                            "cache_read_input_tokens": 200,
                        },
                    },
                },
                {
                    "type": "user",
                    "uuid": "u-meta",
                    "timestamp": "2026-10-10T12:01:00.000Z",
                    "isMeta": True,
                    "message": {"role": "user", "content": "meta noise"},
                },
                {
                    "type": "assistant",
                    "uuid": "a-side",
                    "timestamp": "2026-10-10T12:01:01.000Z",
                    "isSidechain": True,
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 999,
                            "output_tokens": 999,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    },
                },
            ],
        )

    def test_backfill_idempotent_and_categories(self):
        n1, files = session_usage.backfill(
            self.live, projects_dir=self.projects, classify=False
        )
        self.assertEqual(files, 1)
        self.assertEqual(n1, 1)
        n2, _ = session_usage.backfill(
            self.live, projects_dir=self.projects, classify=False
        )
        self.assertEqual(n2, 0)
        with (self.live / "state" / "usage-history.csv").open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "code_dive")
        self.assertEqual(rows[0]["category_source"], "l2a")
        self.assertEqual(rows[0]["user_uuid"], "u1")
        self.assertEqual(int(rows[0]["input_tokens"]), 100)
        self.assertEqual(int(rows[0]["cache_read_input_tokens"]), 200)

    def test_cli_backfill_and_summary(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.live),
                "--projects-dir",
                str(self.projects),
                "--backfill",
                "--summary",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("rows_appended=1", r.stdout)
        self.assertIn("code_dive", r.stdout)

    def test_classify_without_claude_cli_skips(self):
        # unlabeled turn + --claude pointing at a missing binary
        _write_jsonl(
            self.projects / "sess-bbb.jsonl",
            [
                {
                    "type": "user",
                    "uuid": "u2",
                    "timestamp": "2026-10-11T12:00:00.000Z",
                    "message": {"role": "user", "content": "hmm maybe something vague"},
                },
                {
                    "type": "assistant",
                    "uuid": "a2",
                    "timestamp": "2026-10-11T12:00:05.000Z",
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    },
                },
            ],
        )
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.live),
                "--projects-dir",
                str(self.projects),
                "--backfill",
                "--classify",
                "--claude",
                str(self.tmp / "no-such-claude-binary"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.live / "logs" / "usage-classify-runs.csv"
        self.assertTrue(log.is_file())
        self.assertIn("skipped", log.read_text(encoding="utf-8"))
        self.assertIn("claude CLI not on PATH", log.read_text(encoding="utf-8"))

    def test_classify_via_fake_claude_p_bulk(self):
        fake = self.tmp / "fake-claude"
        # Emit one TSV line per numbered turn in the prompt
        fake.write_text(
            "#!/bin/sh\n"
            "# argv: -p <prompt> --model haiku --permission-mode dontAsk\n"
            "prompt=\"$2\"\n"
            "echo \"$prompt\" | awk '/^[0-9]+\\. /{c++} END{for(i=1;i<=c;i++) print i\"\\tlookup\"}'\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        _write_jsonl(
            self.projects / "sess-ccc.jsonl",
            [
                {
                    "type": "user",
                    "uuid": "u3",
                    "timestamp": "2026-10-11T13:00:00.000Z",
                    "message": {"role": "user", "content": "vague unlabeled ask"},
                },
                {
                    "type": "assistant",
                    "uuid": "a3",
                    "timestamp": "2026-10-11T13:00:05.000Z",
                    "message": {
                        "role": "assistant",
                        "usage": {
                            "input_tokens": 11,
                            "output_tokens": 6,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    },
                },
            ],
        )
        n, _ = session_usage.backfill(
            self.live,
            projects_dir=self.projects,
            classify=True,
            claude_bin=str(fake),
        )
        self.assertGreaterEqual(n, 1)
        with (self.live / "state" / "usage-history.csv").open(encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["message_uuid"] == "a3"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "lookup")
        self.assertEqual(rows[0]["category_source"], "l2b")
        log = (self.live / "logs" / "usage-classify-runs.csv").read_text(encoding="utf-8")
        self.assertIn("bulk", log)

    def test_parse_bulk_labels(self):
        parsed = session_usage._parse_bulk_labels("1\tlookup\n2: prototype\n3|capture\n", 3)
        self.assertEqual(parsed, {1: "lookup", 2: "prototype", 3: "capture"})


class MetricsUsageRowsTests(unittest.TestCase):
    def test_metrics_reads_usage_history(self):
        tmp = Path(tempfile.mkdtemp(prefix="pmwb-m-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        shutil.copy(WORKBENCH / "scripts" / "workbench_metrics.py", tmp / "workbench_metrics.py")
        # run metrics from a fake root: workbench_metrics uses ROOT = parent of scripts/
        root = tmp / "live"
        (root / "scripts").mkdir(parents=True)
        shutil.copy(WORKBENCH / "scripts" / "workbench_metrics.py", root / "scripts" / "workbench_metrics.py")
        (root / "state").mkdir()
        with (root / "state" / "usage-history.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=session_usage.HEADER, lineterminator="\n")
            w.writeheader()
            w.writerow(
                {
                    "session_id": "s",
                    "message_uuid": "m1",
                    "timestamp": "2026-10-01T00:00:00Z",
                    "user_uuid": "u",
                    "user_excerpt": "/brief daily-brief",
                    "category": "workflow:daily-brief",
                    "category_source": "l2a",
                    "input_tokens": "10",
                    "output_tokens": "20",
                    "cache_creation_input_tokens": "100",
                    "cache_read_input_tokens": "50",
                    "model": "x",
                    "is_sidechain": "no",
                    "project": "p",
                    "indexed_date": "2026-10-13",
                }
            )
        r = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "workbench_metrics.py"),
                "--today",
                "2026-10-13",
                "--json",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        metrics = json.loads(r.stdout)["metrics"]
        self.assertEqual(metrics["usage_msgs_30d"], 1)
        self.assertEqual(metrics["usage_input_tokens_30d"], 10)
        self.assertEqual(metrics["usage_output_tokens_30d"], 20)
        self.assertEqual(metrics["usage_cache_read_tokens_30d"], 50)
        self.assertEqual(metrics["usage_l2a_labeled_pct_30d"], 100.0)


if __name__ == "__main__":
    unittest.main()
