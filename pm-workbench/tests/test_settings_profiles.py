"""Deny-list parity and MCP allow-rule shape across Claude Code settings profiles.

Kit profiles must match each other on deny. MCP allows must use server-scoped
wildcards — bare `mcp__*` is skipped by Claude Code and still prompts.
The user-level file at ~/.claude/settings.json is checked only when it exists.
"""
import json
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / ".claude"
PROFILES = ("settings.json", "settings.core.json", "settings.full.json")

REQUIRED_MCP_ALLOWS = (
    "mcp__plugin_atlassian_atlassian__*",
    "mcp__browser-bridge__*",
    "mcp__ux_guardrails__*",
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def deny_list(path):
    deny = load(path).get("permissions", {}).get("deny")
    if not isinstance(deny, list):
        raise AssertionError(f"{path} has no permissions.deny list")
    return deny


def allow_list(path):
    allow = load(path).get("permissions", {}).get("allow")
    if not isinstance(allow, list):
        raise AssertionError(f"{path} has no permissions.allow list")
    return allow


class SettingsDenyParityTests(unittest.TestCase):
    def test_kit_profiles_share_one_deny_list(self):
        base = deny_list(KIT / "settings.json")
        self.assertGreater(len(base), 0)
        for name in PROFILES[1:]:
            self.assertEqual(deny_list(KIT / name), base, name)

    def test_user_settings_match_when_present(self):
        home = Path.home() / ".claude" / "settings.json"
        if not home.is_file():
            self.skipTest("no ~/.claude/settings.json on this machine")
        self.assertEqual(deny_list(home), deny_list(KIT / "settings.json"))


class SettingsMcpAllowTests(unittest.TestCase):
    def test_kit_profiles_allow_atlassian_server_wildcard(self):
        for name in PROFILES:
            allow = allow_list(KIT / name)
            with self.subTest(profile=name):
                self.assertNotIn("mcp__*", allow)
                for rule in REQUIRED_MCP_ALLOWS:
                    self.assertIn(rule, allow, msg=name)

    def test_user_settings_reject_invalid_mcp_star_when_present(self):
        home = Path.home() / ".claude" / "settings.json"
        if not home.is_file():
            self.skipTest("no ~/.claude/settings.json on this machine")
        allow = allow_list(home)
        self.assertNotIn("mcp__*", allow)
        self.assertIn("mcp__plugin_atlassian_atlassian__*", allow)


if __name__ == "__main__":
    unittest.main()
