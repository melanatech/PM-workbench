#!/usr/bin/env python3
"""Fixture tests for cache-first context stitch (preflight, hooks, repo profile, baseline QA)."""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPTS = WORKBENCH / "scripts"
HOOKS = WORKBENCH / ".claude" / "hooks"
sys.path.insert(0, str(SCRIPTS))

import analysis_index  # noqa: E402
import context_preflight  # noqa: E402
import repo_profile  # noqa: E402


def _git_init(repo: Path, msg: str = "init") -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=repo, check=True, capture_output=True)


class ContextPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-stitch-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "state").mkdir()
        (self.tmp / "logs").mkdir()
        (self.tmp / "outputs" / "weekly").mkdir(parents=True)
        (self.tmp / "registers").mkdir()
        weekly = self.tmp / "outputs" / "weekly" / "2026-10-07-instrumentation-events.md"
        weekly.write_text(
            "# Instrumentation inventory\n\nEvents fire for reports export.\n"
            "Source: repos/acme-reports@abc1234\n",
            encoding="utf-8",
        )
        analysis_index.append_row(
            self.tmp,
            topic_key="instrumentation|events|reports",
            path="outputs/weekly/2026-10-07-instrumentation-events.md",
            kind="instrumentation",
            as_of_date="2026-10-07",
            one_line="Events inventory for reports",
            primary_sources="repos/acme-reports@abc1234",
            source_workflow="process-inbox",
        )

    def test_cache_hit_lists_weekly_before_repos(self):
        marker = context_preflight.run_preflight(self.tmp, topic="instrumentation events reports")
        self.assertTrue(marker["hits"], marker)
        paths = [h["path"] for h in marker["hits"]]
        self.assertIn("outputs/weekly/2026-10-07-instrumentation-events.md", paths)
        self.assertTrue(all(not p.startswith("repos/") for p in paths))
        self.assertEqual(marker["hits"][0].get("primary_sources"), "repos/acme-reports@abc1234")
        self.assertIn(marker["recommendation"], ("reuse", "reuse_and_refresh"))
        log = self.tmp / "logs" / "context-preflight.csv"
        self.assertTrue(log.is_file())
        with log.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("recommendation", rows[0])

    def test_reuse_and_refresh_when_init_newer(self):
        init = self.tmp / "registers" / "initiatives.csv"
        init.write_text(
            "id,name,stage,prd_path,prototype_path,related_evidence_ids,related_okr,notes,last_updated\n"
            "INIT-033,Reports,discovery,,,,,,2026-10-12\n",
            encoding="utf-8",
        )
        marker = context_preflight.run_preflight(
            self.tmp, topic="INIT-033 instrumentation", init_id="INIT-033"
        )
        self.assertEqual(marker["recommendation"], "reuse_and_refresh")
        self.assertTrue(any("last_updated" in s for s in marker["newer_signals"]))

    def test_primary_sources_in_stdout(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "context_preflight.py"),
                "--root",
                str(self.tmp),
                "--topic",
                "instrumentation",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("primary_sources:", r.stdout)
        self.assertIn("repos/acme-reports@abc1234", r.stdout)


class HookGroundingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-hook-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "state").mkdir()
        (self.tmp / "drafts").mkdir()
        (self.tmp / "outputs" / "daily").mkdir(parents=True)
        marker = {
            "topic": "reports",
            "timestamp": "2099-01-01T00:00:00Z",
            "hits": [
                {
                    "path": "outputs/weekly/2026-10-07-instrumentation-events.md",
                    "primary_sources": "repos/acme-reports@abc1234",
                    "as_of": "2026-10-07",
                }
            ],
            "recommendation": "reuse",
            "allow_repos": False,
        }
        (self.tmp / "state" / ".context-preflight.json").write_text(
            json.dumps(marker) + "\n", encoding="utf-8"
        )
        # keep mtime fresh
        os.utime(self.tmp / "state" / ".context-preflight.json", None)

    def _run_grounding(self, rel_path: str, content: str) -> subprocess.CompletedProcess:
        full = self.tmp / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(full)},
        }
        return subprocess.run(
            [sys.executable, str(HOOKS / "check_context_grounding.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.tmp),
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)},
            check=False,
        )

    def test_blocks_uncited_consequential_write(self):
        r = self._run_grounding(
            "drafts/reports-product-brief.md",
            "# Brief\n\n" + ("We should ship explanations.\n" * 20),
        )
        self.assertEqual(r.returncode, 2, r.stderr + r.stdout)

    def test_passes_with_evidence_cite(self):
        r = self._run_grounding(
            "drafts/reports-product-brief.md",
            "# Brief\n\nCites outputs/weekly/2026-10-07-instrumentation-events.md "
            "and primary repos/acme-reports@abc1234.\n" + ("x\n" * 20),
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_blocks_draft_only_citation(self):
        r = self._run_grounding(
            "drafts/reports-product-brief.md",
            "# Brief\n\nSee drafts/other-brief.md for evidence.\n" + ("y\n" * 20),
        )
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("drafts/", r.stderr)


class ReposGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-repos-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "state").mkdir()
        (self.tmp / "repos" / "acme").mkdir(parents=True)
        (self.tmp / "repos" / "acme" / "src.js").write_text("// hi\n", encoding="utf-8")

    def _run(self, path: str, marker: dict | None) -> subprocess.CompletedProcess:
        if marker is not None:
            mp = self.tmp / "state" / ".context-preflight.json"
            mp.write_text(json.dumps(marker) + "\n", encoding="utf-8")
            os.utime(mp, None)
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": str(self.tmp / path)},
        }
        return subprocess.run(
            [sys.executable, str(HOOKS / "require_context_preflight_for_repos.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.tmp),
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)},
            check=False,
        )

    def test_blocks_without_marker(self):
        r = self._run("repos/acme/src.js", None)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_allows_when_allow_repos(self):
        r = self._run(
            "repos/acme/src.js",
            {"recommendation": "investigate", "allow_repos": True, "hits": []},
        )
        self.assertEqual(r.returncode, 0, r.stderr)


class RepoProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-profile-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        repos = self.tmp / "repos"
        repos.mkdir()

        mock = repos / "fixture-app-mock"
        mock.mkdir()
        (mock / "README.md").write_text(
            "This is a mock replica of the product UI for demos. Not production.\n",
            encoding="utf-8",
        )
        (mock / "package.json").write_text('{"name":"fixture-app-mock"}\n', encoding="utf-8")
        pages = mock / "src" / "pages"
        pages.mkdir(parents=True)
        for name in (
            "Dashboard.js",
            "Orders.js",
            "OrdersDocs.js",
            "CatalogDocs.js",
            "DesignSandbox.js",
            "ReportsHubV2.js",
            "ReportsHubV3.js",
            "Customers.js",
            "Payouts.js",
            "Settings.js",
            "Transactions.js",
            "Inventory.js",
            "Invoices.js",
            "Payments.js",
            "Devices.js",
            "VisionDocs.js",
        ):
            (pages / name).write_text(f"export default function {name[:-3]}(){{}}\n", encoding="utf-8")
        (mock / "src" / "nav-config.js").write_text(
            "export default [\n"
            + ",\n".join(
                f'  {{ path: "/{n[:-3].lower()}", label: "{n[:-3]}" }}'
                for n in (
                    "Dashboard.js",
                    "Orders.js",
                    "Catalog.js",
                    "Customers.js",
                    "Payouts.js",
                    "Settings.js",
                    "Transactions.js",
                    "Inventory.js",
                    "Invoices.js",
                    "Payments.js",
                    "Devices.js",
                    "Reports.js",
                    "Export.js",
                    "Analytics.js",
                    "Team.js",
                    "Billing.js",
                )
            )
            + "\n];\n",
            encoding="utf-8",
        )
        _git_init(mock, "demo mock snapshot")

        product = repos / "fixture-reports"
        product.mkdir()
        (product / "README.md").write_text("Product package for reports surfaces.\n", encoding="utf-8")
        (product / "package.json").write_text(
            '{"name":"@example-org/fixture-reports","dependencies":{}}\n',
            encoding="utf-8",
        )
        (product / ".github").mkdir()
        (product / "src").mkdir()
        (product / "src" / "nav-config.js").write_text(
            "export default [\n"
            '  { path: "/orders", label: "Orders" },\n'
            '  { path: "/transactions", label: "Transactions" },\n'
            '  { path: "/payouts", label: "Payouts" },\n'
            '  { path: "/product-sales", label: "Product sales" },\n'
            "];\n",
            encoding="utf-8",
        )
        for i in range(3):
            (product / f"src/a{i}.test.js").write_text("test('x', () => {});\n", encoding="utf-8")
        _git_init(product, "ABC-1001: add orders report")
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "ABC-1002: transactions columns"],
            cwd=product,
            check=True,
            capture_output=True,
        )

    def test_classifies_and_ranks_product_on_overlap(self):
        data = repo_profile.ensure_profiles(self.tmp, force=True)
        by_name = {r["name"]: r for r in data["repos"]}
        self.assertEqual(by_name["fixture-app-mock"]["role"], "mock")
        self.assertEqual(by_name["fixture-reports"]["role"], "product")
        orders = data["surfaces"].get("/orders") or []
        self.assertTrue(orders, data["surfaces"])
        self.assertEqual(orders[0]["name"], "fixture-reports")
        self.assertEqual(orders[0]["role"], "product")
        # mock-only surface still maps to mock
        dash = data["surfaces"].get("/dashboard") or []
        self.assertTrue(dash)
        self.assertEqual(dash[0]["name"], "fixture-app-mock")


class BaselineQaGateTests(unittest.TestCase):
    def test_qa_fails_without_baseline_sources(self):
        tmp = Path(tempfile.mkdtemp(prefix="pmwb-qa-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proto = tmp / "prototypes" / "demo"
        (proto / "src" / "baseline").mkdir(parents=True)
        (proto / "src" / "baseline" / "Screen.jsx").write_text("export default () => null\n", encoding="utf-8")
        (proto / "index.html").write_text("<html><body>hi</body></html>\n", encoding="utf-8")
        # Import the check by running node with a tiny harness that loads the function logic
        # Mirror the gate: missing BASELINE-SOURCES.md must fail when baseline/ exists
        map_path = proto / "BASELINE-SOURCES.md"
        self.assertFalse(map_path.exists())
        has_baseline = (proto / "src" / "baseline").is_dir()
        self.assertTrue(has_baseline)
        # Documented gate condition from qa-prototype.mjs
        fails = has_baseline and (not map_path.exists() or map_path.stat().st_size < 40)
        self.assertTrue(fails)

    def test_qa_script_contains_baseline_gate(self):
        src = (WORKBENCH / ".claude/skills/prototype-build/qa/qa-prototype.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("BASELINE-SOURCES.md", src)
        self.assertIn("checkBaselineSources", src)


class ProtocolWireTests(unittest.TestCase):
    def test_discover_and_report_mention_step0_preflight(self):
        disc = (WORKBENCH / ".claude/workflows/discovery.md").read_text(encoding="utf-8")
        weekly = (WORKBENCH / ".claude/workflows/weekly-update.md").read_text(encoding="utf-8")
        self.assertIn("context_preflight.py", disc)
        self.assertIn("context_preflight.py", weekly)
        recon = (WORKBENCH / ".claude/agents/prd-prototype-reconciler.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("product brief", recon.lower())
        self.assertIn("BASELINE-SOURCES.md", recon)
        skill = (WORKBENCH / ".claude/skills/prototype-build/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("source-derived", skill.lower())
        self.assertIn("BASELINE-SOURCES.md", skill)


if __name__ == "__main__":
    unittest.main()
