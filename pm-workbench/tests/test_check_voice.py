"""Voice check: team-facing drafts are judged, not scanned for a phrase list."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import check_voice  # noqa: E402

HOOK = KIT / ".claude" / "hooks" / "check_voice.py"
STIFF = (
    "The product is the answer, not the pipe. "
    "What follows is the framing for how to think about the bet. "
    "Key takeaways are listed below so the reader can align on the narrative."
)


class ScopeTests(unittest.TestCase):
    def test_prds_briefs_and_shares_are_in(self):
        for rel in (
            "outputs/prds/reporting/prd.md",
            "drafts/reporting-product-brief.md",
            "outputs/weekly/2026-11-05-leadership-update.md",
            "outputs/external/share.md",
            "outputs/strategy/readout.html",
        ):
            self.assertTrue(check_voice.is_team_facing(rel), rel)

    def test_technical_files_are_out(self):
        for rel in (
            "scripts/check_voice.py",
            "learning/area.md",
            ".claude/workflows/prd-package.md",
            "registers/decisions.csv",
            "outputs/prds/reporting/notes.json",
        ):
            self.assertFalse(check_voice.is_team_facing(rel), rel)

    def test_audience_frontmatter_is_in(self):
        text = "---\naudience: external\n---\nHello\n"
        self.assertTrue(check_voice.is_team_facing("notes/share.md", text))


class RubricTests(unittest.TestCase):
    def test_live_section_is_the_rubric(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            style = root / "reference" / "context"
            style.mkdir(parents=True)
            (style / "writing-style.md").write_text(
                "## External writing (shares)\n\nSound like this person when writing for the team.\n\n## Examples\n\nIgnore.\n",
                encoding="utf-8",
            )
            rubric = check_voice.rubric_for(root)
            self.assertIn("Sound like this person when writing for the team.", rubric)
            self.assertNotIn("Ignore.", rubric)

    def test_missing_live_file_uses_the_kit_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            rubric = check_voice.rubric_for(Path(tmp))
            self.assertIn("lead with what you want them to look at.", rubric)


class JudgeTests(unittest.TestCase):
    def test_fail_quotes_the_draft(self):
        def ask(prompt):
            self.assertIn("person on the team", prompt)
            self.assertIn("The product is the answer", prompt)
            return json.dumps({
                "pass": False,
                "notes": [{"quote": "The product is the answer, not the pipe.", "why": "the sentence sets up its opposite"}],
            })

        verdict = check_voice.evaluate(STIFF, check_voice.DEFAULT_RUBRIC, ask=ask)
        self.assertFalse(verdict.ok)
        self.assertIn("not the pipe", verdict.notes[0].quote)
        message = check_voice.report("outputs/prds/x/prd.md", verdict)
        self.assertIn("not the pipe", message)
        self.assertIn("once more to confirm", message)

    def test_one_pass_returns_every_note(self):
        notes = [{"quote": f"Sentence {n}.", "why": "memo"} for n in range(8)]

        def ask(prompt):
            self.assertIn("List every problem", prompt)
            self.assertNotIn("At most 6", prompt)
            return json.dumps({"pass": False, "notes": notes})

        verdict = check_voice.evaluate(STIFF, check_voice.DEFAULT_RUBRIC, ask=ask)
        self.assertEqual(len(verdict.notes), 8)

    def test_a_spent_counter_still_judges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / ".voice-check-2026-11-05.count").write_text("30", encoding="utf-8")
            seen = {}

            def ask(prompt):
                seen["asked"] = True
                return '{"pass": true}'

            verdict = check_voice.judge("We should ship the read-only connection for three reports.", root, ask=ask, relative="outputs/prds/x/prd.md")
            self.assertTrue(seen.get("asked"))
            self.assertTrue(verdict.ok)

    def test_unavailable_says_to_save(self):
        verdict = check_voice.Verdict(False, [], unavailable="the judge returned nothing")
        message = check_voice.report("outputs/prds/x/prd.md", verdict)
        self.assertIn("Save the file", message)
        self.assertIn("not a voice failure", message)

    def test_the_judge_call_is_not_saved_as_a_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "argv.txt"
            fake = Path(tmp) / "fake_claude.py"
            fake.write_text(
                "#!/usr/bin/env python3\nimport os, sys\n"
                f"open({str(record)!r}, 'w').write(' '.join(sys.argv[1:]) + '\\n'"
                "+ os.getcwd() + '\\n' + os.environ.get('SESSION_MEMORY_INTERNAL', '') + '\\n')\n"
                "print('{\"pass\": true}')\n"
            )
            fake.chmod(0o755)
            with mock.patch.dict(os.environ, {"VOICE_CHECK_CLAUDE": str(fake)}):
                for leaked in ("CHECK_VOICE_REPLY", "VOICE_CHECK_CWD"):
                    os.environ.pop(leaked, None)
                self.assertIsNotNone(check_voice.ask_model("Judge this."))
            argv, cwd, internal = record.read_text().splitlines()
            flags = argv.split()
            for flag in ("--no-session-persistence", "--tools", "--strict-mcp-config",
                         "--disable-slash-commands", "--system-prompt"):
                self.assertIn(flag, flags)
            self.assertIn("claude-lean-call", cwd)
            self.assertNotEqual(os.path.abspath(cwd), os.path.abspath(tmp))
            self.assertEqual(internal, "1")

    def test_pass_is_quiet(self):
        verdict = check_voice.evaluate("We should ship the read-only connection for three reports.", check_voice.DEFAULT_RUBRIC, ask=lambda _p: '{"pass": true}')
        self.assertTrue(verdict.ok)

    def test_code_fence_is_not_what_gets_judged(self):
        seen = {}

        def ask(prompt):
            seen["prompt"] = prompt
            return '{"pass": true}'

        text = "The customer opens the report and reads the table.\n\n```\n{\"not\": \"a sentence\"}\n```\n"
        check_voice.evaluate(text, check_voice.DEFAULT_RUBRIC, ask=ask)
        self.assertNotIn('{"not": "a sentence"}', seen["prompt"])
        self.assertIn("The customer opens the report and reads the table.", seen["prompt"])


class HookTests(unittest.TestCase):
    def _run(self, relative, tool, fields, reply):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = tmp
            env["CHECK_VOICE_REPLY"] = reply
            payload = {
                "tool_name": tool,
                "tool_input": {"file_path": str(Path(tmp) / relative), **fields},
            }
            return subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

    def test_write_of_a_stiff_prd_is_blocked(self):
        result = self._run(
            "outputs/prds/reporting/prd.md",
            "Write",
            {"content": STIFF},
            json.dumps({"pass": False, "notes": [{"quote": "The product is the answer, not the pipe.", "why": "reframe"}]}),
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not the pipe", result.stderr)

    def test_short_edit_is_allowed(self):
        result = self._run(
            "outputs/prds/reporting/prd.md",
            "Edit",
            {"old_string": "v1", "new_string": "version one"},
            json.dumps({"pass": False, "notes": [{"quote": "nope", "why": "should not run"}]}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_write_is_allowed(self):
        result = self._run(
            "scripts/helper.py",
            "Write",
            {"content": STIFF},
            json.dumps({"pass": False, "notes": [{"quote": "nope", "why": "should not run"}]}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unavailable_judge_allows_the_write(self):
        result = self._run(
            "outputs/prds/reporting/prd.md",
            "Write",
            {"content": STIFF},
            "not json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("did not run", result.stderr)


if __name__ == "__main__":
    unittest.main()
