"""Tests for the cluster commands: routes table, router files, runner, run-log naming, health report."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
ROUTES = WORKBENCH / ".claude" / "workflows" / "routes.json"
PROTOCOL = WORKBENCH / ".claude" / "workflows" / "_protocol.md"
COMMANDS = WORKBENCH / ".claude" / "commands"
RUNNER = WORKBENCH / ".claude" / "agents" / "workflow-runner.md"
LOG_HOOK = WORKBENCH / ".claude" / "hooks" / "log_run.py"
HEALTH = WORKBENCH / "scripts" / "workbench_health.py"
STANDALONE = {"quick-close", "todo"}
MODELS = {"haiku", "sonnet", "opus"}


def clusters():
    return json.loads(ROUTES.read_text(encoding="utf-8"))["clusters"]


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    block = text.split("---")[1] if text.startswith("---") else ""
    return dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", block, re.M))


class RoutesTableTests(unittest.TestCase):
    def test_every_workflow_file_is_routed_exactly_once(self):
        routed = [w for ws in clusters().values() for w in ws]
        self.assertEqual(len(routed), len(set(routed)), "a workflow is listed in two clusters")
        files = {p.stem for p in (WORKBENCH / ".claude" / "workflows").glob("*.md") if not p.name.startswith("_")}
        self.assertEqual(files | {"prototype-build"}, set(routed))

    def test_paths_exist_and_models_are_valid_and_match_frontmatter(self):
        for cluster, workflows in clusters().items():
            for name, entry in workflows.items():
                path = WORKBENCH / entry["path"]
                self.assertTrue(path.is_file(), f"{cluster}:{name} -> {entry['path']} missing")
                self.assertIn(entry["model"], MODELS, f"{cluster}:{name}")
                declared = frontmatter(path).get("model")
                if declared:
                    self.assertEqual(declared, entry["model"], f"{name}: routes.json and its file disagree on model")

    def test_workflows_are_not_also_registered_as_commands(self):
        registered = {p.stem for p in COMMANDS.glob("*.md")}
        routed = {w for ws in clusters().values() for w in ws}
        self.assertFalse(registered & routed, "a workflow is still a slash command")
        self.assertEqual(registered, set(clusters()) | STANDALONE)

    def test_high_stakes_workflows_stay_on_opus(self):
        flat = {w: e["model"] for ws in clusters().values() for w, e in ws.items()}
        for name in ("prd-package", "strategy-refresh", "experiment-package"):
            self.assertEqual(flat[name], "opus")

    def test_get_started_is_brief_haiku_and_mentions_bootstrap(self):
        flat = {w: e for ws in clusters().values() for w, e in ws.items()}
        self.assertIn("get-started", clusters()["brief"])
        self.assertEqual(flat["get-started"]["model"], "haiku")
        text = (WORKBENCH / ".claude" / "workflows" / "get-started.md").read_text(encoding="utf-8")
        self.assertIn("create_live_workspace.py", text)
        self.assertIn("Open Folder", text)
        self.assertIn("~/pm-live", text)
        skill = (WORKBENCH / ".claude" / "skills" / "get-started" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/brief get-started", skill)
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("/brief get-started", claude)
        self.assertIn("how do i get started", claude.lower())

    def test_gates_survive_the_move(self):
        # The moved files must still carry their execution-mode line or required-input rule.
        for name in ("prd-package", "launch-package", "experiment-package", "strategy-refresh"):
            text = (WORKBENCH / ".claude" / "workflows" / f"{name}.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?i)execution mode|not ready|required input|usage estimate", name)

    def test_meeting_closeout_filters_eng_only_commitments(self):
        text = (WORKBENCH / ".claude" / "workflows" / "meeting-closeout.md").read_text(encoding="utf-8")
        self.assertIn("PM-scope filter", text)
        self.assertIn("Do not log as a commitment", text)
        self.assertIn("SSL", text)
        self.assertIn("engineering keep-list", text)
        inbox = (WORKBENCH / ".claude" / "workflows" / "process-inbox.md").read_text(encoding="utf-8")
        self.assertIn("engineering keep-list", inbox)
        self.assertIn("_source-triage.md", inbox)
        self.assertIn("intake_status.py", inbox)
        self.assertNotIn("paste the full stdout", inbox)
        self.assertIn("one intake line only", inbox)
        self.assertIn("House-format / template detect", inbox)
        self.assertIn("Tier 2 PROPOSAL", inbox)
        self.assertIn("found-templates-index.md", inbox)
        self.assertIn("Forbidden:", inbox)
        self.assertIn("index-only", inbox)
        skill = (WORKBENCH / ".claude" / "skills" / "process-inbox" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("paste **full stdout**", skill)
        self.assertIn("one line only", skill)
        self.assertIn("Tier 2 PROPOSAL", skill)
        self.assertIn("Auto-writing a new template", skill)
        index = (WORKBENCH / "reference" / "templates" / "found-templates-index.md").read_text(encoding="utf-8")
        self.assertIn("Index row ≠ template", index)
        self.assertIn("index-only", index)
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("found-templates-index.md", claude)
        self.assertIn("PROPOSE creating the `.md`", claude)

    def test_discovery_synthesis_checklist_for_modes_1_3_4(self):
        text = (WORKBENCH / ".claude" / "workflows" / "discovery.md").read_text(encoding="utf-8")
        self.assertIn("Synthesis checklist", text)
        self.assertIn("modes 1, 3, and 4", text)
        self.assertIn("Channel mix named", text)
        self.assertIn("Theme cards", text)
        self.assertIn("Independent-account count", text)
        self.assertIn("inferred never counted as customer proof", text)
        self.assertIn("Proactive", text)
        self.assertIn("Reactive", text)
        self.assertIn("Competitive", text)

    def test_gatherer_requires_prior_workspace_analysis_before_repos(self):
        gatherer = (
            WORKBENCH / ".claude" / "agents" / "prd-context-gatherer.md"
        ).read_text(encoding="utf-8")
        explore = (
            WORKBENCH / ".claude" / "workflows" / "explore-brief.md"
        ).read_text(encoding="utf-8")
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("context_preflight", gatherer)
        self.assertIn("consume preflight", gatherer.lower())
        self.assertIn("Prior workspace analysis", gatherer)
        self.assertIn(".context-preflight.json", gatherer)
        self.assertLess(
            gatherer.lower().index("preflight"),
            gatherer.lower().rfind("repos/"),
        )
        self.assertIn("context_preflight", explore)
        self.assertIn("preflight", explore.lower())
        self.assertIn("instrumentation", claude.lower())
        self.assertIn("context_preflight", claude)
        self.assertIn("Cache-first", claude)

    def test_prototype_soft_reuse_catalog_and_shared_package(self):
        design = WORKBENCH / "reference" / "design"
        catalog = (design / "prototype-components.md").read_text(encoding="utf-8")
        shared = (design / "shared-prototype-package.md").read_text(encoding="utf-8")
        self.assertFalse((design / "DEFERRED-shared-prototype-package.md").exists())
        skill = (
            WORKBENCH / ".claude" / "skills" / "prototype-build" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("soft reuse", catalog.lower())
        self.assertIn("prototypes/", catalog)
        self.assertIn("in `_shared`", catalog)
        self.assertIn("prototypes/_shared", shared)
        self.assertIn("file:", shared)
        self.assertIn("npm run share", shared)
        readme = (design / "README.md").read_text(encoding="utf-8")
        self.assertIn("shared-prototype-package.md", readme)
        self.assertNotIn("DEFERRED-shared-prototype-package.md", readme)
        self.assertIn("prototype-components.md", skill)
        self.assertIn("Shared kit", skill)
        self.assertIn("Catalog update", skill)
        self.assertIn("npm run share", skill)
        backlog = (WORKBENCH / "BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("shared-prototype-package.md", backlog)

    def test_explore_brief_reuses_gatherer_and_frames_before_options(self):
        flat = {w: e for ws in clusters().values() for w, e in ws.items()}
        self.assertIn("explore-brief", clusters()["discover"])
        self.assertEqual(flat["explore-brief"]["model"], "sonnet")
        path = WORKBENCH / flat["explore-brief"]["path"]
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("prd-context-gatherer", text)
        self.assertIn("Assemble before options", text)
        self.assertIn("Step 2 — Frame", text)
        self.assertIn("Step 4 — Options", text)
        self.assertLess(text.index("Step 2 — Frame"), text.index("Step 4 — Options"))
        self.assertIn("drafts/", text)
        self.assertNotIn("explore-context-gatherer", text)
        gatherer = (WORKBENCH / ".claude" / "agents" / "prd-context-gatherer.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("explore-brief", gatherer)
        self.assertIn("Decided vs open", gatherer)
        skill = (WORKBENCH / ".claude" / "skills" / "explore-brief" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/discover explore-brief", skill)
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("/discover explore-brief", claude)
        self.assertIn("check-in brief", claude.lower())
        plain = (WORKBENCH / ".claude" / "workflows" / "_plain-language.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("explore-brief", plain)
        prd = (WORKBENCH / ".claude" / "workflows" / "prd-package.md").read_text(encoding="utf-8")
        self.assertIn("/discover explore-brief", prd)
        # No second gatherer agent
        self.assertFalse(
            (WORKBENCH / ".claude" / "agents" / "explore-context-gatherer.md").exists()
        )

    def test_competitive_scan_landscape_and_capture_taxonomy(self):
        scan = (WORKBENCH / ".claude" / "workflows" / "competitive-scan.md").read_text(encoding="utf-8")
        self.assertIn("Landscape", scan)
        self.assertIn("direct", scan)
        self.assertIn("adjacent", scan)
        self.assertIn("emerging", scan)
        self.assertIn("white-space", scan)
        self.assertIn("grounded in", scan)
        self.assertIn("state/competitive", scan)
        self.assertIn("web_search.py", scan)
        self.assertIn("_web-search.md", scan)
        self.assertIn('Should I create the competitive-log?', scan)
        capture = (WORKBENCH / ".claude" / "agents" / "competitive-capture-agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("heading order", capture)
        self.assertIn("## Summary", capture)
        self.assertIn("## By product area", capture)
        self.assertIn("## Changes", capture)
        self.assertIn("## Inferences", capture)
        self.assertIn("## BLOCKED / UNVERIFIED", capture)
        self.assertIn("Direct offering", capture)
        self.assertIn("Positioning / packaging", capture)
        self.assertIn("Gaps vs watch areas", capture)
        self.assertIn("Customer alternatives / workarounds", capture)
        self.assertIn("web_search.py", capture)
        self.assertIn("state/competitive", capture)
        self.assertIn("_web-search.md", capture)

    def test_scenario_guide_optional_prototype_recipe(self):
        recipe = (WORKBENCH / ".claude" / "workflows" / "_scenario-guide.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("look", recipe)
        self.assertIn("ScenarioGuide", recipe)
        skill = (WORKBENCH / ".claude" / "skills" / "scenario-guide" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("_scenario-guide.md", skill)
        proto = (WORKBENCH / ".claude" / "skills" / "prototype-build" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("scenario-guide", proto)
        self.assertIn("prototype-preflight.md", proto)
        lessons = (WORKBENCH / "reference" / "design" / "prototype-preflight.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Standing preflight", lessons)

    def test_web_search_first_class_recipe_and_brief_prd_axes(self):
        recipe = (WORKBENCH / ".claude" / "workflows" / "_web-search.md").read_text(encoding="utf-8")
        self.assertIn("web_search.py", recipe)
        self.assertIn("state/web-search/", recipe)
        for axis in ("Problems", "Market / category", "Users", "Solutions"):
            self.assertIn(axis, recipe)
        fan = (WORKBENCH / ".claude" / "workflows" / "_fan-out.md").read_text(encoding="utf-8")
        self.assertIn("state/web-search/", fan)
        explore = (WORKBENCH / ".claude" / "workflows" / "explore-brief.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("_web-search.md", explore)
        self.assertIn("problems, market/category, users, and solutions", explore)
        prd = (WORKBENCH / ".claude" / "workflows" / "prd-package.md").read_text(encoding="utf-8")
        self.assertIn("_web-search.md", prd)
        self.assertIn("problems, market/category, users, and solutions", prd)
        skill = (WORKBENCH / ".claude" / "skills" / "web-search" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("_web-search.md", skill)
        self.assertIn("web_search.py", skill)
        index_src = (WORKBENCH / "scripts" / "analysis_index.py").read_text(encoding="utf-8")
        self.assertIn('"web-search"', index_src)
        layout = (WORKBENCH / "scripts" / "workspace_layout.py").read_text(encoding="utf-8")
        self.assertIn("state/web-search", layout)
        preflight = (WORKBENCH / "scripts" / "context_preflight.py").read_text(encoding="utf-8")
        self.assertIn("state/web-search", preflight)

    def test_optional_company_product_ui_base_docs(self):
        """Org-agnostic recipe for private UI mocks under live repos/ — no company remotes in kit."""
        setup = (WORKBENCH / "NEW-USER-SETUP.md").read_text(encoding="utf-8")
        self.assertIn("## 2a. Optional: company product UI base", setup)
        self.assertIn("Product UI base (optional)", setup)
        self.assertIn("Source-derived greenfield", setup)
        self.assertIn("BASELINE-SOURCES.md", setup)
        self.assertIn("repo_profile.py", setup)
        self.assertIn("ln -s", setup)
        self.assertIn("CLAUDE.local.md", setup)
        self.assertIn("links.csv", setup)
        self.assertIn("prototypes/", setup)
        self.assertIn("repos/", setup)
        self.assertIn("private npm registry", setup)
        self.assertIn("re-clone", setup)
        self.assertNotIn("gdcorp-commerce", setup)
        self.assertNotIn("pm-ch-mockup", setup)
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("product UI base", claude)
        self.assertIn("NEW-USER-SETUP §2a", claude)
        dive = (WORKBENCH / ".claude" / "workflows" / "code-dive.md").read_text(encoding="utf-8")
        self.assertIn("symlink", dive)
        evolving = (WORKBENCH / "EVOLVING.md").read_text(encoding="utf-8")
        self.assertIn("product UI base", evolving)
        self.assertIn("symlink into live `repos/`", evolving)

    def test_jira_ticket_draft_template_is_paste_ready(self):
        path = WORKBENCH / "reference" / "templates" / "jira-ticket-draft.md"
        self.assertTrue(path.is_file(), path)
        text = path.read_text(encoding="utf-8")
        for phrase in ("Summary:", "Initiative / Epic", "Priority:", "Target date:",
                       "Related tickets:", "do not paste into Jira", "COM-",
                       "Quality checklist", "Find the right epic",
                       "Check what already exists", "verifiable",
                       "Link related tickets formally", "Verify Jira field values"):
            self.assertIn(phrase, text)
        # Org project keys and product-area examples stay out of the kit template
        for banned in ("REPORT", "CP-", "all interactive reports", "Commerce Reporting"):
            self.assertNotIn(banned, text)
        closeout = (WORKBENCH / ".claude" / "workflows" / "meeting-closeout.md").read_text(encoding="utf-8")
        self.assertIn("reference/templates/jira-ticket-draft.md", closeout)
        self.assertIn("Related tickets", closeout)
        self.assertIn("quality checklist", closeout)

    def test_course_catalog_shows_the_full_router_invocation_for_every_workflow(self):
        course = (WORKBENCH.parent / "docs" / "index.html").read_text(encoding="utf-8")
        start = course.index("help:{cmd:'/'")
        end = course.index("Plain language works too", start)
        catalog = course[start:end]
        for cluster, workflows in clusters().items():
            for workflow in workflows:
                with self.subTest(cluster=cluster, workflow=workflow):
                    self.assertIn(f"/{cluster} {workflow}", catalog)
        self.assertNotIn("meeting-closeout, process-inbox:", catalog)
        for workflows in clusters().values():
            for workflow in workflows:
                self.assertIsNone(
                    re.search(rf"(?<![\w-])/{re.escape(workflow)}(?![\w-])", course),
                    f"course still invokes the retired /{workflow} command directly",
                )


class RouterFileTests(unittest.TestCase):
    def test_each_router_is_thin_haiku_and_reads_the_protocol(self):
        for cluster in clusters():
            text = (COMMANDS / f"{cluster}.md").read_text(encoding="utf-8")
            meta = frontmatter(COMMANDS / f"{cluster}.md")
            self.assertEqual(meta.get("model"), "haiku", cluster)
            self.assertIn(".claude/workflows/_protocol.md", text, cluster)
            self.assertIn(f"CLUSTER = `{cluster}`", text, cluster)
            self.assertLess(len(text.splitlines()), 60, f"{cluster} router is no longer thin")

    def test_each_router_names_every_one_of_its_workflows(self):
        for cluster, workflows in clusters().items():
            text = (COMMANDS / f"{cluster}.md").read_text(encoding="utf-8")
            for name in workflows:
                self.assertIn(f"`{name}`", text, f"/{cluster} does not mention {name}")

    def test_protocol_keeps_the_safety_steps(self):
        text = PROTOCOL.read_text(encoding="utf-8")
        for phrase in ("workflow-runner", "usage estimate", "state/.run-workflow", "BLOCKED", "inline",
                       "QUESTIONS", "PROPOSALS", "RESULT", "never writes to a register"):
            self.assertIn(phrase, text)
        self.assertIn("never remove one", text)

    def test_compact_output_is_required_of_protocol_and_runner(self):
        protocol = PROTOCOL.read_text(encoding="utf-8")
        runner = RUNNER.read_text(encoding="utf-8")
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Compact output", protocol)
        self.assertIn("Do not paraphrase", protocol)
        self.assertIn("Relay = paste, then stop", protocol)
        self.assertIn("No RESULT + Done pair", protocol)
        self.assertIn("omit empty", protocol.lower())
        self.assertIn("Every existing workspace path is a clickable Markdown link", claude)
        self.assertIn("show the link **once**", claude)
        self.assertNotIn("Show RESULT text in full", protocol)
        self.assertIn("omit empty negatives", runner)
        self.assertIn("Never paste the same summary twice", runner)
        self.assertIn("Ran <cluster>/<workflow> on <model>", runner)
        self.assertIn("Do **not** mention the Stop hook", runner)
        self.assertNotIn("Run-log note, one line", runner)
        self.assertIn("workspace-relative", protocol)
        self.assertIn("workspace-relative", runner)
        self.assertIn("Never stop on \"ready.\"", protocol)
        self.assertIn("Do not announce readiness and wait", protocol)
        self.assertNotIn("[relative-path](file:///", runner)
        self.assertIn("workspace-relative", claude)
        self.assertIn("Do not mention the git clone vs live-folder", runner)
        self.assertNotIn("End with one line naming the workflow that ran and the model it ran on.", protocol)

    def test_runner_cannot_bypass_approval_rules_and_returns_three_blocks(self):
        text = RUNNER.read_text(encoding="utf-8")
        meta = frontmatter(RUNNER)
        self.assertEqual(meta.get("name"), "workflow-runner")
        self.assertNotIn("tools", meta, "the runner must inherit tools so workflows can run")
        for phrase in ("RESULT", "PROPOSALS", "QUESTIONS", "Never send", "rule 9", "run-manifest"):
            self.assertIn(phrase, text)


class RunLogNamingTests(unittest.TestCase):
    def run_hook(self, prompt, marker=None, marker_age=0):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "logs").mkdir()
            (root / "state").mkdir()
            if marker is not None:
                path = root / "state" / ".run-workflow"
                path.write_text(marker, encoding="utf-8")
                if marker_age:
                    old = path.stat().st_mtime - marker_age
                    os.utime(path, (old, old))
            transcript = root / "t.jsonl"
            transcript.write_text(json.dumps({
                "type": "user", "timestamp": "2020-01-01T00:00:00Z",
                "message": {"role": "user", "content": prompt}}) + "\n", encoding="utf-8")
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(root)
            result = subprocess.run([sys.executable, str(LOG_HOOK)], cwd=root, env=env, text=True,
                                    input=json.dumps({"transcript_path": str(transcript)}),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (root / "logs" / "run-log.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            return rows, (root / "state" / ".run-workflow").exists()

    def test_marker_names_the_workflow_and_is_removed(self):
        rows, still_there = self.run_hook("/build spec out bulk export", marker="build:prd-package")
        self.assertEqual(rows[-1]["workflow"], "build:prd-package")
        self.assertFalse(still_there)

    def test_first_argument_is_the_fallback(self):
        rows, _ = self.run_hook("/report weekly-update for leadership")
        self.assertEqual(rows[-1]["workflow"], "report:weekly-update")

    def test_unknown_workflow_is_logged_as_unspecified(self):
        rows, _ = self.run_hook("/build do something")
        self.assertEqual(rows[-1]["workflow"], "build:unspecified")

    def test_marker_for_another_cluster_is_ignored(self):
        rows, _ = self.run_hook("/build do something", marker="report:okr-refresh")
        self.assertEqual(rows[-1]["workflow"], "build:unspecified")

    def test_standalone_commands_log_as_before(self):
        rows, _ = self.run_hook("/quick-close met with Dana, 3 weeks")
        self.assertEqual(rows[-1]["workflow"], "quick-close")


class HealthReportTests(unittest.TestCase):
    def test_health_lists_cluster_workflows_and_standalone_commands(self):
        result = subprocess.run([sys.executable, str(HEALTH)], cwd=WORKBENCH, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("/quick-close", "/todo", "/build:prd-package", "/capture:meeting-closeout"):
            self.assertIn(name, result.stdout)
        self.assertNotIn("| /build |", result.stdout)


class DocsUseTheNewNamesTests(unittest.TestCase):
    def test_lesson_zero_explains_and_links_to_the_system_download(self):
        course = (WORKBENCH.parent / "docs" / "index.html").read_text(encoding="utf-8")
        start = course.index("V.l0=`")
        end = course.index("V.l1=`", start)
        lesson_zero = course[start:end]
        for text in (
            "Download the PM Workbench system from GitHub",
            "https://github.com/melanatech/PM-workbench",
            "Code → Download ZIP",
            "inner <code>pm-workbench</code> folder",
            "~/pm-live",
            "create_live_workspace.py",
            "NEW-USER-SETUP.md",
            "first</b> (or only) folder",
        ):
            with self.subTest(text=text):
                self.assertIn(text, lesson_zero)

    def test_course_teaches_pm_scope_and_jira_draft_rules(self):
        course = (WORKBENCH.parent / "docs" / "index.html").read_text(encoding="utf-8")
        l2 = course[course.index("V.l2=`"):course.index("V.l3=`")]
        l4 = course[course.index("V.l4=`"):course.index("V.l5=`")]
        self.assertIn("Eng-only chores", l2)
        self.assertIn("Promises you own, chase, or depend on", l2)
        self.assertIn("Registers stay PM-scoped", l4)
        self.assertIn("jira-ticket-draft.md", l4)
        self.assertIn("Related</b> means other Jira tickets only", l4)
        # Course lessons must not teach clipper/DOM or Stop-hook plumbing
        lessons = "".join(
            course[course.index(f"V.l{i}=`"):course.index(f"V.l{i+1}=`" if i < 10 else "V.fin=`")]
            for i in range(0, 11)
            if f"V.l{i}=`" in course
        )
        self.assertNotIn("aria_setsize", lessons)
        self.assertNotIn("Stop hook", lessons)
        self.assertNotIn("virtualized", lessons)

    def test_scheduling_and_menu_script_call_the_routers(self):
        scheduling = (WORKBENCH / "SCHEDULING.md").read_text(encoding="utf-8")
        menu = (WORKBENCH / "Run PM Workflow.command").read_text(encoding="utf-8")
        for text in (scheduling, menu):
            self.assertIn("/brief daily-brief", text)
        self.assertNotRegex(menu, r'cmd="/(daily-brief|prd-package|meeting-closeout|discovery)\b')

    def test_settings_do_not_reference_removed_commands(self):
        for name in ("settings.json", "settings.core.json", "settings.full.json"):
            data = json.loads((WORKBENCH / ".claude" / name).read_text(encoding="utf-8"))
            for key in data.get("skillOverrides", {}):
                self.assertTrue((COMMANDS / f"{key}.md").exists() or (WORKBENCH / ".claude" / "skills" / key).exists(), f"{name}: {key}")


class RoadmapAndStrategyFromScratchTests(unittest.TestCase):
    def test_roadmap_build_is_report_sonnet_and_phrases_route(self):
        report = clusters()["report"]
        self.assertEqual(report["roadmap-build"]["model"], "sonnet")
        self.assertEqual(report["roadmap-build"]["path"], ".claude/workflows/roadmap-build.md")
        self.assertEqual(report["strategy-refresh"]["model"], "opus")
        text = (WORKBENCH / ".claude" / "workflows" / "roadmap-build.md").read_text(encoding="utf-8")
        self.assertIn("Execution mode: **standard**", text)
        self.assertIn("Deep upgrades", (WORKBENCH / ".claude" / "commands" / "report.md").read_text(encoding="utf-8"))
        self.assertIn("dispatch `workflow-runner` on opus", text)
        self.assertIn("routes.json", text)
        self.assertNotIn("model: opus", text.split("---", 2)[1])
        for phrase in (
            "Discovery phase",
            "discovery-source-reader",
            "competitive-capture-agent",
            "web_search.py",
            "state/competitive/",
            "do not re-scan",
            "context_health.py",
            "derived, not stated priorities",
            "one batched QUESTIONS",
            "before sequencing",
            "No invented dates",
            "[NEEDS INPUT]",
            "Now / Next / Later",
            "strategy-red-team-reviewer",
            "Anticipated objections",
            "Do not silently rewrite",
            "not impersonation",
            "optional persona lenses",
            "Not in the default flow",
            "external-readiness-reviewer",
            "audience: internal",
            "formats: [md]",
            "Do not call a wiki create API",
            "BLOCKED: confirm derived priorities",
            "12 source",
        ):
            self.assertIn(phrase, text, phrase)
        self.assertIn("Fast does not dispatch it", text)
        self.assertLess(text.index("Discovery phase"), text.index("Cold start"))
        self.assertLess(text.index("Cold start"), text.index("## Sequence"))
        self.assertLess(text.index("## Sequence"), text.index("## Red team"))
        self.assertTrue(text.rstrip().endswith("Do not call a wiki create API or a chat send API from this step."))

    def test_plain_language_skill_and_router_name_the_phrases(self):
        plain = (WORKBENCH / ".claude" / "workflows" / "_plain-language.md").read_text(encoding="utf-8")
        self.assertIn("Build a roadmap", plain)
        self.assertIn("draft a roadmap from scratch", plain)
        self.assertIn("/report roadmap-build", plain)
        self.assertIn("Strategy from scratch", plain)
        self.assertIn("draft a strategy from scratch", plain)
        self.assertIn("/sync roadmap-update", plain)
        skill = (WORKBENCH / ".claude" / "skills" / "roadmap-build" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/report roadmap-build", skill)
        self.assertIn("build a roadmap", skill.lower())
        self.assertIn("draft a roadmap from scratch", skill.lower())
        report = (WORKBENCH / ".claude" / "commands" / "report.md").read_text(encoding="utf-8")
        self.assertIn("`roadmap-build`", report)
        self.assertLess(len(report.splitlines()), 60)
        strategy_skill = (WORKBENCH / ".claude" / "skills" / "strategy-refresh" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("strategy from scratch", strategy_skill.lower())

    def test_strategy_refresh_defaults_to_standard_and_has_from_scratch(self):
        text = (WORKBENCH / ".claude" / "workflows" / "strategy-refresh.md").read_text(encoding="utf-8")
        self.assertIn("Execution mode: **standard**", text)
        self.assertNotIn("Execution mode: **deep**", text)
        self.assertIn("model: opus", text)
        self.assertIn("From-scratch mode", text)
        self.assertIn("product-strategy-memo-template.md", text)
        self.assertIn("initial version", text)
        self.assertIn("discovery-source-reader", text)
        self.assertIn("do not re-scan", text.lower())
        self.assertIn("derived, not stated priorities", text)
        self.assertIn("No invented dates", text)
        self.assertIn("strategy-red-team-reviewer", text)
        self.assertIn("Anticipated objections", text)
        self.assertIn("not impersonation", text)
        self.assertIn("external-readiness-reviewer", text)
        self.assertIn("Step 4 — Publish", text)
        self.assertTrue(
            (WORKBENCH / "reference" / "templates" / "product-strategy-memo-template.md").is_file()
        )
        memo = (WORKBENCH / "reference" / "templates" / "product-strategy-memo-template.md").read_text(encoding="utf-8")
        for heading in (
            "Vision statement",
            "Learnings & Discovery",
            "Product Objectives",
            "Key Initiatives",
            "Key dependencies/risks",
        ):
            self.assertIn(heading, memo)
            self.assertIn(heading, text)

    def test_red_team_is_sonnet_and_weekly_update_is_optional(self):
        agent = (WORKBENCH / ".claude" / "agents" / "strategy-red-team-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("model: sonnet", agent)
        self.assertIn("cited sources", agent.lower())
        self.assertIn("Do not silently rewrite", agent)
        self.assertNotIn("model: haiku", agent)
        self.assertNotIn("model: opus", agent)
        weekly = (WORKBENCH / ".claude" / "workflows" / "weekly-update.md").read_text(encoding="utf-8")
        self.assertIn("Optional red team", weekly)
        self.assertIn("Not the default", weekly)
        self.assertIn("not run in Fast", weekly)
        self.assertIn("strategy-red-team-reviewer", weekly)
        self.assertLess(weekly.index("Optional red team"), weekly.index("**Publish.**"))


if __name__ == "__main__":
    unittest.main()
