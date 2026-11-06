"""Tests for the Cursor project hooks in .cursor/hooks (claim check, worker refile, stop gate, dispatch block)."""
import json
from pathlib import Path
import re
import shutil
import sys
import subprocess
import tempfile
import unittest


WORKBENCH = Path(__file__).resolve().parents[1]
KIT_CURSOR = WORKBENCH / ".cursor"
HOOK_EVENTS = {
    "afterFileEdit", "stop", "preToolUse", "subagentStart", "subagentStop",
    "afterAgentResponse", "beforeMCPExecution",
}
FAKE_IDENTITY = {
    "name": "Pat Example",
    "email": "pat@example.com",
    "jira_account_id": "acct-123",
    "username_examples": ["pexample"],
}
SOURCED_TABLE = (
    "## Claim table\n\n| Claim | Source | Checked how |\n|---|---|---|\n"
    "| Item 9 has no PRD ticket | JQL `text ~ \"COGS PRD\"` returned 0 | tracker search |\n"
)


class HookBase(unittest.TestCase):
    identity = FAKE_IDENTITY

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shutil.copytree(
            KIT_CURSOR / "hooks", self.root / ".cursor" / "hooks",
            ignore=shutil.ignore_patterns("pm-identity.json", "dispatch-block.md", "__pycache__"),
        )
        (self.root / "outputs" / "daily").mkdir(parents=True)
        if self.identity:
            (self.root / ".cursor" / "hooks" / "pm-identity.json").write_text(json.dumps(self.identity))

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, script, payload):
        payload = {"workspace_roots": [str(self.root)], "cursor_version": "test", **payload}
        p = subprocess.run(
            ["python3", str(self.root / ".cursor" / "hooks" / script)],
            input=json.dumps(payload), capture_output=True, text=True, cwd=self.root,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout or "{}")

    def stop(self, conversation_id):
        return self.run_hook("stop_gate.py", {"hook_event_name": "stop", "conversation_id": conversation_id,
                                              "status": "completed", "loop_count": 0})

    def worker_stop(self, **kw):
        base = {"hook_event_name": "subagentStop", "subagent_type": "generalPurpose", "subagent_id": "w1",
                "conversation_id": "w1", "parent_conversation_id": "coord", "status": "completed",
                "loop_count": 0, "modified_files": [], "task": "x", "description": "x", "summary": "Done."}
        return self.run_hook("subagent_claims_gate.py", {**base, **kw})


class KitIsGeneric(unittest.TestCase):
    # Names, company, and account ids come from the gitignored terms file via check_kit_generic.
    PERSONAL = re.compile(r"pm-live|/Users/", re.I)

    def test_no_private_terms(self):
        sys.path.insert(0, str(WORKBENCH / "scripts"))
        import check_kit_generic
        self.assertEqual(check_kit_generic.scan(list(KIT_CURSOR.rglob("*"))), [])

    def test_no_person_or_workspace_strings(self):
        for path in KIT_CURSOR.rglob("*"):
            if not path.is_file() or path.name in ("pm-identity.json", "dispatch-block.md") or "__pycache__" in path.parts:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                self.assertIsNone(self.PERSONAL.search(line), f"{path.relative_to(WORKBENCH)}:{n}: {line.strip()[:120]}")

    def test_identity_files_are_gitignored(self):
        ignored = (WORKBENCH / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".cursor/hooks/pm-identity.json", ignored)
        self.assertIn(".cursor/hooks/dispatch-block.md", ignored)
        self.assertTrue((KIT_CURSOR / "hooks" / "pm-identity.example.json").is_file())

    def test_hooks_json_names_real_events_and_scripts(self):
        cfg = json.loads((KIT_CURSOR / "hooks.json").read_text(encoding="utf-8"))
        for event, entries in cfg["hooks"].items():
            self.assertIn(event, HOOK_EVENTS)
            for entry in entries:
                self.assertTrue((WORKBENCH / entry["command"]).is_file(), entry["command"])


class DispatchBlock(HookBase):
    TASK = {"description": "d", "prompt": "Run jira-reconcile and list files.", "subagent_type": "generalPurpose"}

    def test_task_prompt_gets_block_with_identity(self):
        wf = self.root / ".claude" / "workflows" / "jira-reconcile.md"
        wf.parent.mkdir(parents=True)
        wf.write_text("# jira-reconcile\n")
        out = self.run_hook("dispatch_inject.py", {"hook_event_name": "preToolUse", "tool_name": "Task",
                                                    "tool_input": self.TASK})
        prompt = out["updated_input"]["prompt"]
        self.assertTrue(prompt.startswith("[WORKBENCH DISPATCH BLOCK"))
        self.assertIn("Pat Example (pat@example.com; Jira accountId acct-123)", prompt)
        self.assertIn("`pexample`", prompt)
        self.assertIn(".claude/workflows/jira-reconcile.md", prompt)
        self.assertTrue(prompt.endswith(self.TASK["prompt"]))
        again = self.run_hook("dispatch_inject.py", {"hook_event_name": "preToolUse", "tool_name": "Task",
                                                      "tool_input": {**self.TASK, "prompt": prompt}})
        self.assertNotIn("updated_input", again)

    def write_brain(self, text):
        brain = self.root / "reference" / "context" / "pm-brain.md"
        brain.parent.mkdir(parents=True, exist_ok=True)
        brain.write_text(text, encoding="utf-8")

    def dispatch(self):
        out = self.run_hook("dispatch_inject.py", {"hook_event_name": "preToolUse", "tool_name": "Task",
                                                    "tool_input": self.TASK})
        return out["updated_input"]["prompt"]

    def test_saved_rules_reach_the_worker_without_anyone_wiring_them(self):
        self.write_brain("## Roadmap rules\n\n- Status is blockers only.\n")
        self.assertIn("Status is blockers only.", self.dispatch())
        self.write_brain("## Roadmap rules\n\n- Status is blockers only.\n- Every card names its owner.\n")
        self.assertIn("Every card names its owner.", self.dispatch())

    def test_dispatch_records_which_rules_version_the_worker_got(self):
        self.write_brain("- One rule.\n")
        self.dispatch()
        rows = [json.loads(l) for l in (self.root / "state" / "hooks" / "hook-log.jsonl").read_text().splitlines()]
        injected = [r for r in rows if r.get("decision") == "inject"]
        self.assertEqual(len(injected[-1]["standing_rules_version"]), 12)

    def test_rendered_block_tells_the_worker_to_read_the_file(self):
        self.write_brain("- One rule.\n")
        subprocess.run(["python3", str(self.root / ".cursor/hooks/dispatch_inject.py"), "--write-block"],
                       capture_output=True, text=True, cwd=self.root, check=True)
        text = (self.root / ".cursor/hooks/dispatch-block.md").read_text()
        self.assertIn("reference/context/pm-brain.md", text)
        self.assertNotIn("One rule.", text)

    def test_other_tools_untouched(self):
        self.assertEqual(self.run_hook("dispatch_inject.py", {"tool_name": "Read", "tool_input": {"path": "x"}}), {})
        wrapped = {"namespace": "cursor", "toolName": "Task", "arguments": self.TASK}
        self.assertEqual(self.run_hook("dispatch_inject.py", {"tool_name": "CallDynamicTool", "tool_input": wrapped}), {})

    def test_write_block(self):
        p = subprocess.run(["python3", str(self.root / ".cursor/hooks/dispatch_inject.py"), "--write-block"],
                           capture_output=True, text=True, cwd=self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Pat Example", (self.root / ".cursor/hooks/dispatch-block.md").read_text())


class NoIdentity(HookBase):
    identity = None

    def test_block_asks_for_identity(self):
        out = self.run_hook("dispatch_inject.py", {"tool_name": "Task", "tool_input": DispatchBlock.TASK})
        prompt = out["updated_input"]["prompt"]
        self.assertIn("PM: [NEEDS INPUT: PM name/email].", prompt)
        self.assertIn("your OS username or a cloud account name", prompt)


class WorkerClaims(HookBase):
    def test_unsourced_claims_followup(self):
        out = self.worker_stop(summary="Item 9 has no PRD. Assigned to Sam Other.")
        self.assertIn("followup_message", out)

    def test_sourced_table_allows(self):
        self.assertEqual(self.worker_stop(summary="Item 9 has no PRD ticket.\n\n" + SOURCED_TABLE), {})

    def test_wrong_pm_followup_even_with_table(self):
        out = self.worker_stop(summary="Ask the PM (Sam).\n\n" + SOURCED_TABLE)
        self.assertIn("followup_message", out)

    def test_loop_limit_respected(self):
        self.assertEqual(self.worker_stop(loop_count=2, summary="Item 9 has no PRD."), {})

    def test_no_false_positives(self):
        for text in ["Listed 12 files in outputs/daily.", "No changes needed.",
                     "Owner column is empty for 3 rows.", "There is no ticket key in the title, so I used the summary."]:
            self.assertEqual(self.worker_stop(summary=text), {}, text)

    def test_claim_reaches_coordinator_stop(self):
        self.worker_stop(parent_conversation_id="coord2", child_conversation_id="w9",
                         summary="COGS needs a PRD. Assigned to Sam Other.")
        self.assertIn("worker w9 returned", self.stop("coord2").get("followup_message", ""))
        self.assertEqual(self.stop("unrelated"), {})

    def test_subagent_start_is_log_only(self):
        out = self.run_hook("subagent_start.py", {"hook_event_name": "subagentStart", "subagent_type": "generalPurpose",
                                                  "task": "Update outputs/strategy/x.html with the new table.",
                                                  "parent_conversation_id": "coord", "subagent_id": "w0"})
        self.assertEqual(out, {"permission": "allow"})


class FileClaims(HookBase):
    def edit(self, conversation_id, rel, text):
        (self.root / rel).write_text(text, encoding="utf-8")
        self.run_hook("after_file_edit.py", {"hook_event_name": "afterFileEdit", "conversation_id": conversation_id,
                                             "file_path": str(self.root / rel), "edits": []})

    def test_failing_worker_file_blocks_coordinator(self):
        bad = "outputs/daily/claims-fail.md"
        self.edit("w2", bad, "# Fixture\n\nItem 9 has no PRD. Ticket assigned to Sam Other.\n")
        self.edit("w2", "outputs/daily/claims-pass.md", "# Fixture\n\nItem 9 has no PRD.\n\n" + SOURCED_TABLE)
        out = self.worker_stop(subagent_id="w2", conversation_id="w2", modified_files=[bad])
        self.assertIn("followup_message", out)
        self.assertIn(bad, self.stop("coord").get("followup_message", ""))
        status = json.loads((self.root / "state/hooks/gate-status.json").read_text())
        self.assertEqual(status["sessions"]["w2"]["artifacts"]["outputs/daily/claims-pass.md"].get("claims"), "pass")


class RelayRecorder(HookBase):
    def test_unsourced_relay_blocks_next_stop(self):
        self.run_hook("relay_claims_check.py", {"hook_event_name": "afterAgentResponse", "conversation_id": "relay",
                                                "generation_id": "g1", "text": "Needs a PRD: COGS. Assigned to Sam Other."})
        self.assertIn("earlier reply", self.stop("relay").get("followup_message", ""))


if __name__ == "__main__":
    unittest.main()
