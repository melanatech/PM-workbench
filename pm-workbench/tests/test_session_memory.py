"""Plan E Part 2: session-memory hooks (fixtures and a fake `claude`; no model, no real ~/.claude)."""
import datetime
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
MODULE = WORKBENCH.parent / "session-memory"
HOOKS = MODULE / "hooks"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(WORKBENCH / "scripts"))

FAKE = """#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[2]
if os.environ.get('FAKE_ARGV'):
    open(os.environ['FAKE_ARGV'], 'a').write(
        ' '.join(sys.argv[3:]) + '\\nCWD ' + os.getcwd()
        + '\\nINTERNAL ' + os.environ.get('SESSION_MEMORY_INTERNAL', '') + '\\n')
open(os.environ['FAKE_CALLS'], 'a').write(prompt.split('# Task: ')[-1][:80].replace('\\n', ' ') + '\\n')
replies = json.load(open(os.environ['FAKE_REPLIES']))
for key, reply in replies.items():
    if key in prompt:
        print(reply)
        sys.exit(0)
print('{"ops": []}')
"""


def ts(minutes_ago):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)).isoformat()


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}, "timestamp": ts(1)}


def assistant(text, minutes_ago=1, tokens=1000):
    return {"type": "assistant", "timestamp": ts(minutes_ago),
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}],
                        "usage": {"input_tokens": 10, "cache_read_input_tokens": tokens, "cache_creation_input_tokens": 0}}}


class Base(unittest.TestCase):
    def setUp(self):
        # The project key follows CLAUDE_PROJECT_DIR; a runner started inside Claude Code has it set.
        self._project_dir = os.environ.pop("CLAUDE_PROJECT_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "sm-home"
        self.cwd = self.tmp / "project"
        self.cwd.mkdir()
        self.fake = self.tmp / "fake_claude.py"
        self.fake.write_text(FAKE)
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.calls = self.tmp / "calls.txt"
        self.replies = {}
        self.transcript = self.tmp / "t.jsonl"

    def tearDown(self):
        self._tmp.cleanup()
        if self._project_dir is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = self._project_dir

    def write_transcript(self, rows):
        self.transcript.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def env(self, **extra):
        (self.tmp / "replies.json").write_text(json.dumps(self.replies))
        env = {**os.environ, "SESSION_MEMORY_HOME": str(self.home), "SESSION_MEMORY_CLAUDE": str(self.fake),
               "SESSION_MEMORY_SYNC": "1", "FAKE_CALLS": str(self.calls),
               "FAKE_REPLIES": str(self.tmp / "replies.json")}
        env.pop("SESSION_MEMORY_INTERNAL", None)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.update(extra)
        return env

    def payload(self, **kw):
        return {"session_id": "s1", "cwd": str(self.cwd), "transcript_path": str(self.transcript), **kw}

    def run_hook(self, name, payload, raw=None, expect=0, **env):
        p = subprocess.run([sys.executable, str(HOOKS / name)], input=raw if raw is not None else json.dumps(payload),
                           capture_output=True, text=True, env=self.env(**env))
        self.last_hook = p
        self.assertEqual(p.returncode, expect, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def register(self, sid="s1"):
        import common
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        try:
            return common.load_entries(common.register_path({"cwd": str(self.cwd), "session_id": sid}))
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)

    def active(self, sid="s1"):
        import common
        return common.active_entries(self.register(sid))

    def call_log(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []


class FailOpen(Base):
    def test_bad_cursor_and_internal_payloads_do_nothing(self):
        for name in ("keeper.py", "restore.py", "prompt.py", "reading.py"):
            self.assertIsNone(self.run_hook(name, None, raw="not json"))
            cursor = self.payload(conversation_id="c1", cursor_version="2.0", source="compact", prompt="hello there friend")
            self.assertIsNone(self.run_hook(name, cursor))
            self.assertIsNone(self.run_hook(name, self.payload(source="compact", prompt="x" * 40),
                                            SESSION_MEMORY_INTERNAL="1"))
        self.assertFalse(self.home.exists())
        self.assertEqual(self.call_log(), [])

    def test_missing_transcript_is_harmless(self):
        self.assertIsNone(self.run_hook("keeper.py", self.payload(transcript_path=str(self.tmp / "nope.jsonl"))))


class SupersessionParity(unittest.TestCase):
    def test_same_rule_as_register_view(self):
        import common
        import register_view
        cases = [
            [("e1", []), ("e2", ["e1"]), ("e3", ["e2"])],
            [("e1", []), ("e2", []), ("e3", ["e1", "e2"])],
            [("e1", ["e2"]), ("e2", [])],
            [("e1", ["e1"])],
        ]
        for case in cases:
            entries = [{"id": i, "section": "Decisions", "text": i, "supersedes": s} for i, s in case]
            rows = [{"id": i, "supersedes": ";".join(s)} for i, s in case]
            self.assertEqual([e["id"] for e in common.active_entries(entries)],
                             [r["id"] for r in register_view.active_rows(rows)], case)


class Keeper(Base):
    def capture(self, prompt, reply="ok"):
        rows = json.loads("[" + ",".join(self.transcript.read_text().splitlines()) + "]") if self.transcript.exists() else []
        self.write_transcript(rows + [user(prompt), assistant(reply)])
        self.run_hook("keeper.py", self.payload())

    def test_decision_lands_and_small_talk_adds_nothing(self):
        self.replies = {"use CSV": '{"ops": [{"op": "add", "section": "Decisions", "text": "Export as CSV, not PDF"}]}'}
        self.capture("Let's use CSV for the export, not PDF, final answer.")
        self.capture("thanks")
        self.assertEqual([(e["section"], e["text"]) for e in self.active()], [("Decisions", "Export as CSV, not PDF")])
        self.assertEqual(len(self.call_log()), 1)

    def test_reversal_supersedes_and_a_later_goal_add_does_not_replace_the_subject(self):
        self.replies = {"first goal": '{"ops": [{"op": "add", "section": "Goal", "text": "Pick a vendor"}, '
                                      '{"op": "add", "section": "Decisions", "text": "Vendor A"}]}'}
        self.capture("The first goal: pick a vendor, and we go with vendor A.")
        self.replies = {"vendor B": '{"ops": [{"op": "supersede", "ids": ["e2"], "section": "Decisions", "text": "Vendor B"}, '
                                    '{"op": "add", "section": "Goal", "text": "Contract vendor B"}]}'}
        self.capture("Actually go with vendor B, A cannot do SSO.")
        active = self.active()
        self.assertEqual([e["text"] for e in active if e["section"] == "Goal"], ["Pick a vendor"])
        self.assertEqual([e["text"] for e in active if e["section"] == "Where it stands"], ["Contract vendor B"])
        self.assertEqual([e["text"] for e in active if e["section"] == "Decisions"], ["Vendor B"])
        self.assertIn("correction signal", self.call_log()[-1])
        self.assertNotIn("correction signal", self.call_log()[0])

    def test_audit_every_tenth_capture(self):
        self.replies = {"Task: capture": '{"ops": [{"op": "add", "section": "Constraints", "text": "No new deps"}]}',
                        "Task: audit": '{"ops": [{"op": "drop", "ids": ["e1"]}]}'}
        for n in range(10):
            self.capture(f"Message number {n} with enough words to count")
        self.assertIn("audit", " ".join(self.call_log()))
        self.assertNotIn("e1", [e["id"] for e in self.active()])

    def test_daily_call_cap_skips_and_logs(self):
        self.replies = {"Task: capture": '{"ops": [{"op": "add", "section": "Decisions", "text": "D"}]}'}
        env_cap = {"SESSION_MEMORY_DAILY_CALLS": "1"}
        self.write_transcript([user("A decision worth keeping, long enough"), assistant("ok")])
        self.run_hook("keeper.py", self.payload(), **env_cap)
        self.write_transcript([user("Another decision worth keeping, long enough"), assistant("ok")])
        self.run_hook("keeper.py", self.payload(), **env_cap)
        self.assertEqual(len(self.call_log()), 1)
        log = (next(self.home.glob("*/log.jsonl"))).read_text()
        self.assertIn("capture-failed", log)


class HeadlessCalls(Base):
    def test_hook_model_calls_are_not_saved_as_sessions(self):
        self.replies = {"Task: capture": '{"ops": []}'}
        self.write_transcript([user("A decision worth keeping, long enough to count"), assistant("ok")])
        argv = self.tmp / "argv.txt"
        self.run_hook("keeper.py", self.payload(), FAKE_ARGV=str(argv))
        self.assertTrue(argv.exists(), "the model was never called")
        lines = argv.read_text().splitlines()
        flags = lines[0].split()
        for flag in ("--no-session-persistence", "--tools", "--strict-mcp-config",
                     "--disable-slash-commands", "--system-prompt"):
            self.assertIn(flag, flags)
        self.assertIn("claude-lean-call", lines[1])
        self.assertEqual(lines[2], "INTERNAL 1")


class ProjectKey(Base):
    def test_register_follows_the_project_not_the_folder_the_agent_moved_into(self):
        import common
        sub = self.cwd / "outputs" / "v3"
        sub.mkdir(parents=True)
        self.replies = {"use CSV": '{"ops": [{"op": "add", "section": "Decisions", "text": "Export as CSV"}]}'}
        self.write_transcript([user("Let's use CSV for the export, final answer."), assistant("ok")])
        self.run_hook("keeper.py", self.payload(cwd=str(sub)), CLAUDE_PROJECT_DIR=str(self.cwd))
        key = common.slug(str(self.cwd))
        self.assertTrue((self.home / key / "s1.jsonl").exists())
        self.assertEqual([p.name for p in self.home.iterdir() if p.is_dir()], [key])

    def test_without_the_env_var_the_nearest_claude_folder_is_the_project(self):
        import common
        (self.cwd / ".claude").mkdir()
        sub = self.cwd / "drafts" / "deep"
        sub.mkdir(parents=True)
        self.assertEqual(common.project_root(str(sub)), str(self.cwd))
        self.assertEqual(common.project_root(str(self.cwd)), str(self.cwd))

    def test_a_folder_with_no_claude_parent_is_its_own_project(self):
        import common
        self.assertEqual(common.project_root(str(self.cwd)), str(self.cwd))

    def test_pickup_from_a_subfolder_finds_the_projects_registers(self):
        import common
        sub = self.cwd / "outputs"
        sub.mkdir()
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.cwd)
        try:
            common.update_index({"cwd": str(sub), "session_id": "old1"}, goal="Parser rewrite")
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        found = subprocess.run([sys.executable, str(MODULE / "pickup.py"), "--cwd", str(self.cwd), "parser"],
                               capture_output=True, text=True, env=self.env(CLAUDE_PROJECT_DIR=str(self.cwd)))
        self.assertIn("old1", found.stdout)


class Restore(Base):
    def test_compact_prints_only_active_entries_with_preface(self):
        import common
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        try:
            path = common.register_path(self.payload())
            common.append_entries(path, [
                {"id": "e1", "section": "Constraints", "text": "Old rule", "supersedes": []},
                {"id": "e2", "section": "Constraints", "text": "New rule", "supersedes": ["e1"]},
                {"id": "e3", "section": "Corrections", "text": "Say the PM, not a username", "supersedes": []}])
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)
        out = self.run_hook("restore.py", self.payload(source="compact"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("just compacted", ctx)
        self.assertIn("New rule", ctx)
        self.assertNotIn("Old rule", ctx)
        self.assertIn("never edits that file itself", ctx)

    def test_startup_offers_waiting_review_once(self):
        (self.home / "reviews").mkdir(parents=True)
        (self.home / "reviews" / "2026-11-02.md").write_text("# review\n")
        self.assertIn("weekly review", self.run_hook("restore.py", self.payload(source="startup"))
                      ["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.run_hook("restore.py", self.payload(source="startup")))


class Prompt(Base):
    def test_reminder_every_prompt_exempts_judgment_work(self):
        self.write_transcript([user("hi"), assistant("hello")])
        out = self.run_hook("prompt.py", self.payload(prompt="next step please"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("session-reader", ctx)
        self.assertIn("partner skill", ctx)
        self.assertNotIn("systemMessage", out)

    def test_nudge_is_included_once(self):
        self.home.mkdir(parents=True)
        (self.home / "nudge.txt").write_text("Use the browser bridge when WebFetch is blocked.")
        self.write_transcript([user("hi"), assistant("hello")])
        first = self.run_hook("prompt.py", self.payload(prompt="search the web"))
        self.assertIn("browser bridge", first["hookSpecificOutput"]["additionalContext"])
        self.assertFalse((self.home / "nudge.txt").exists())
        second = self.run_hook("prompt.py", self.payload(prompt="search again"))
        self.assertNotIn("browser bridge", second["hookSpecificOutput"]["additionalContext"])

    def test_stale_large_session_is_blocked_until_force(self):
        self.replies = {"Task: snapshot": '{"ops": [{"op": "add", "section": "Where it stands", "text": "Draft 2 done"}]}'}
        self.write_transcript([user("write the doc"), assistant("done", minutes_ago=120, tokens=150000)])
        out = self.run_hook("prompt.py", self.payload(prompt="what next"), expect=2,
                            SESSION_MEMORY_FLOOR_TOKENS="0")
        self.assertIsNone(out)
        self.assertIn("idle 2.0 h", self.last_hook.stderr)
        self.assertIn("was not sent", self.last_hook.stderr)
        self.assertIn("what next", self.last_hook.stderr)
        self.assertEqual([e["text"] for e in self.active()], ["Draft 2 done"])
        forced = self.run_hook("prompt.py", self.payload(prompt="!force what next"),
                               SESSION_MEMORY_FLOOR_TOKENS="0")
        self.assertNotIn("was not sent", forced["hookSpecificOutput"]["additionalContext"])

    def test_growth_within_a_new_chat_is_not_blocked(self):
        self.write_transcript([user("write the doc"), assistant("done", minutes_ago=120, tokens=150000)])
        out = self.run_hook("prompt.py", self.payload(prompt="what next"), SESSION_MEMORY_FLOOR_TOKENS="100000")
        self.assertNotIn("was not sent", out["hookSpecificOutput"]["additionalContext"])

    def test_growth_above_a_new_chat_names_the_saving(self):
        self.replies = {"Task: snapshot": '{"ops": []}'}
        self.write_transcript([user("write the doc"), assistant("done", minutes_ago=120, tokens=200000)])
        self.run_hook("prompt.py", self.payload(prompt="what next"), expect=2, SESSION_MEMORY_FLOOR_TOKENS="100000")
        self.assertIn("100k tokens more than a new chat", self.last_hook.stderr)

    def test_small_or_recent_session_no_notice(self):
        self.write_transcript([user("x"), assistant("y", minutes_ago=120, tokens=5000)])
        self.assertNotIn("systemMessage", self.run_hook("prompt.py", self.payload(prompt="go")))
        self.write_transcript([user("x"), assistant("y", minutes_ago=5, tokens=200000)])
        self.assertNotIn("systemMessage", self.run_hook("prompt.py", self.payload(prompt="go")))

    def seed_old_session(self):
        import common
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        try:
            common.update_index({"cwd": str(self.cwd), "session_id": "old1"}, goal="Pricing page rewrite")
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)

    def test_detector_offers_match_and_prefers_none(self):
        self.seed_old_session()
        self.write_transcript([user("Continue the pricing page rewrite from yesterday please")])
        self.replies = {"Prefer none": '{"session": "old1"}'}
        out = self.run_hook("prompt.py", self.payload(prompt="Continue the pricing page rewrite from yesterday please"))
        self.assertIn("old1", out["hookSpecificOutput"]["additionalContext"])
        self.replies = {"Prefer none": '{"session": "made-up"}'}
        out = self.run_hook("prompt.py", self.payload(session_id="s2", prompt="Something unrelated about the roadmap deck"))
        self.assertNotIn("earlier session", out["hookSpecificOutput"]["additionalContext"])


class Reading(Base):
    def read(self, path, size=40000, **extra):
        return self.run_hook("reading.py", self.payload(tool_name="Read", tool_input={"file_path": path},
                                                        tool_response="x" * size, **extra))

    def test_notice_once_past_budget(self):
        self.run_hook("prompt.py", self.payload(prompt="go"))
        self.assertIsNone(self.read("/a.md", size=1000))
        out = self.read("/b.md", size=120000)
        self.assertIn("session-reader", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.read("/c.md", size=120000))
        self.run_hook("prompt.py", self.payload(prompt="go again"))
        self.assertIsNotNone(self.read("/d.md", size=120000))

    def test_partner_session_is_exempt(self):
        self.run_hook("prompt.py", self.payload(prompt="help me think about the strategy"))
        self.read("/kit/.claude/skills/partner/SKILL.md", size=100)
        self.assertIsNone(self.read("/strategy.md", size=200000))

    def test_subagent_calls_are_not_counted(self):
        self.assertIsNone(self.read("/big.md", size=200000, agent_id="sub-1"))


class Install(Base):
    def install(self, *args):
        return subprocess.run([sys.executable, str(MODULE / "install.py"), "--home", str(self.tmp / "home"), *args],
                              capture_output=True, text=True)

    def test_install_is_idempotent_keeps_other_hooks_and_uninstalls_cleanly(self):
        claude = self.tmp / "home" / ".claude"
        claude.mkdir(parents=True)
        original = {"model": "x", "hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "gocode notify"}]}]}}
        (claude / "settings.json").write_text(json.dumps(original))
        (claude / "CLAUDE.md").write_text("# mine\n")
        dry = self.install("--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads((claude / "settings.json").read_text()), original)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install().returncode, 0)
        settings = json.loads((claude / "settings.json").read_text())
        stop_cmds = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(len(stop_cmds), 2)
        self.assertIn("gocode notify", stop_cmds)
        self.assertEqual(sorted(settings["hooks"]), ["PostToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        self.assertEqual((claude / "CLAUDE.md").read_text().count("BEGIN SESSION MEMORY"), 1)
        self.assertTrue((claude / "agents" / "session-reader.md").exists())
        self.assertNotIn("SESSION_MEMORY_DIR", (claude / "commands" / "pickup.md").read_text())
        self.assertTrue(list(claude.glob("settings.json.session-memory-backup-*")))
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(json.loads((claude / "settings.json").read_text()), original)
        self.assertEqual((claude / "CLAUDE.md").read_text(), "# mine\n")
        self.assertFalse((claude / "agents" / "session-reader.md").exists())


class Pickup(Base):
    def test_adopt_copies_kept_entries_with_source(self):
        import common
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        try:
            p = {"cwd": str(self.cwd), "session_id": "old1"}
            common.append_entries(common.register_path(p), [
                {"id": "e1", "section": "Constraints", "text": "No new deps", "supersedes": []},
                {"id": "e2", "section": "Don't retry", "text": "Regex parser failed", "supersedes": []}])
            common.update_index(p, goal="Parser rewrite")
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)
        env = self.env()
        found = subprocess.run([sys.executable, str(MODULE / "pickup.py"), "--cwd", str(self.cwd), "parser"],
                               capture_output=True, text=True, env=env)
        self.assertIn("old1", found.stdout)
        done = subprocess.run([sys.executable, str(MODULE / "pickup.py"), "--cwd", str(self.cwd), "--adopt", "old1",
                               "--keep", "e2", "--session", "new1"], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([(e["text"], e["source"]) for e in self.active("new1")], [("Regex parser failed", "old1:e2")])

    def test_a_todo_goal_still_matches_words_in_the_register(self):
        import common
        os.environ["SESSION_MEMORY_HOME"] = str(self.home)
        try:
            payload = {"cwd": str(self.cwd), "session_id": "old1"}
            common.append_entries(common.register_path(payload), [
                {"id": "e1", "section": "Goal", "text": "Get approval on the definitions table", "supersedes": []},
                {"id": "e2", "section": "Where it stands", "text": "Reseller commission explorer and the plan are drafted", "supersedes": []}])
            common.update_index(payload, goal="Get approval on the definitions table")
        finally:
            os.environ.pop("SESSION_MEMORY_HOME", None)
        found = subprocess.run([sys.executable, str(MODULE / "pickup.py"), "--cwd", str(self.cwd),
                                "reseller", "commission", "report", "planning"],
                               capture_output=True, text=True, env=self.env())
        self.assertIn("old1", found.stdout)
        self.assertIn("reseller", found.stdout)


if __name__ == "__main__":
    unittest.main()
