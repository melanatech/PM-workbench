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

    def test_gates_survive_the_move(self):
        # The moved files must still carry their execution-mode line or required-input rule.
        for name in ("prd-package", "launch-package", "experiment-package", "strategy-refresh"):
            text = (WORKBENCH / ".claude" / "workflows" / f"{name}.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?i)execution mode|not ready|required input|usage estimate", name)

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
        ):
            with self.subTest(text=text):
                self.assertIn(text, lesson_zero)

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


if __name__ == "__main__":
    unittest.main()
