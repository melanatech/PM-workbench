"""Deny-list parity across Claude Code settings profiles.

Kit profiles must match each other. The user-level file at ~/.claude/settings.json
is checked only when it exists, so CI on a machine without that file still passes.
"""
import json
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / ".claude"
PROFILES = ("settings.json", "settings.core.json", "settings.full.json")


def deny_list(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    deny = data.get("permissions", {}).get("deny")
    if not isinstance(deny, list):
        raise AssertionError(f"{path} has no permissions.deny list")
    return deny


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


if __name__ == "__main__":
    unittest.main()
