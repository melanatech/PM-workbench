"""Clipper scroll policy: a stuck scroll position is not the end of the list."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "tools" / "workbench-clipper" / "scroll-policy.js"
BACKGROUND = ROOT / "tools" / "workbench-clipper" / "background.js"


class ClipperScrollPolicyTest(unittest.TestCase):
    def test_background_no_longer_stops_at_six_bottom_stalls(self):
        text = BACKGROUND.read_text()
        self.assertNotIn("stallRounds >= 6", text)
        self.assertNotIn("stallRounds >= 12", text)
        self.assertNotIn("missing.slice(0, 40)", text)
        self.assertNotIn("missing.slice(0, 80)", text)
        self.assertIn("scroll-policy.js", text)
        self.assertIn("noteProbe", text)

    def test_note_probe_ignores_a_false_bottom(self):
        script = r"""
const policy = require(process.argv[1]);
const stuck = { countGrew: false, heightGrew: false };
let dead = 0;
let gaveUp = false;
for (let i = 0; i < 7; i++) {
  const v = policy.noteProbe(dead, stuck);
  dead = v.dead;
  gaveUp = v.giveUp;
}
if (gaveUp) process.exit(2);
const grown = policy.noteProbe(7, { countGrew: false, heightGrew: true });
if (grown.dead !== 0 || grown.giveUp) process.exit(3);
const eighth = policy.noteProbe(7, stuck);
if (!eighth.giveUp || eighth.dead !== 8) process.exit(4);
const ranges = policy.formatMissing([1, 2, 3, 5, 8, 9]);
if (ranges !== '1-3,5,8-9') process.exit(5);
const top = policy.scrollTopForPos(1000, 200, 51, 101);
if (top !== 400) process.exit(6);
"""
        result = subprocess.run(
            ["node", "-e", script, str(POLICY)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stderr or result.stdout or f"exit {result.returncode}",
        )


if __name__ == "__main__":
    unittest.main()
