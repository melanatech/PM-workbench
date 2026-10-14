"""Stream transcript parse + clipper v0.6 static checks + incomplete gate."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))

import stream_transcript_parse as stp  # noqa: E402

CLIPPER = WORKBENCH / "tools" / "workbench-clipper"
WORKFLOWS = WORKBENCH / ".claude" / "workflows"
FIXTURE = WORKBENCH / "tests" / "fixtures" / "stream-transcript-sample.html"


class ParseSpeakerLabelTests(unittest.TestCase):
    def test_minutes_seconds(self):
        sp, t = stp.parse_speaker_label("Alex Rivera 3 minutes 12 seconds")
        self.assertEqual(sp, "Alex Rivera")
        self.assertEqual(t, "3:12")

    def test_hours(self):
        sp, t = stp.parse_speaker_label("Alex Rivera 1 hours 2 minutes 5 seconds")
        self.assertEqual(sp, "Alex Rivera")
        self.assertEqual(t, "1:02:05")

    def test_continuation_still_has_speaker(self):
        sp, t = stp.parse_speaker_label("Alex Rivera 1 hours 2 minutes 9 seconds")
        self.assertEqual(sp, "Alex Rivera")
        self.assertEqual(t, "1:02:09")

    def test_no_duration(self):
        sp, t = stp.parse_speaker_label("Someone")
        self.assertEqual(sp, "Someone")
        self.assertEqual(t, "")


class FormatAndGapTests(unittest.TestCase):
    def test_merge_same_speaker(self):
        by_pos = {
            22: {"speaker": "Alex Rivera", "time": "3:12", "text": "First."},
            23: {"speaker": "Alex Rivera", "time": "3:18", "text": "Second."},
            24: {"speaker": "Sam Chen", "time": "3:40", "text": "Question?"},
        }
        out = stp.format_transcript(by_pos)
        self.assertIn("**Alex Rivera** [3:12]: First. Second.", out)
        self.assertIn("**Sam Chen** [3:40]: Question?", out)
        self.assertEqual(out.count("**Alex Rivera**"), 1)

    def test_missing_positions(self):
        by_pos = {1: {}, 2: {}, 4: {}}
        miss = stp.missing_positions(by_pos, 4)
        self.assertEqual(miss, [3])
        self.assertEqual(stp.missing_positions(by_pos, 0), [])

    def test_incomplete_only_when_gaps(self):
        full = {i: {} for i in range(1, 6)}
        self.assertEqual(stp.missing_positions(full, 5), [])
        self.assertTrue(bool(stp.missing_positions({1: {}, 2: {}}, 5)))


class VttTests(unittest.TestCase):
    def test_parse_vtt_with_voice_tags(self):
        vtt = """WEBVTT

1
00:00:03.000 --> 00:00:05.000
<v Alex Rivera>Hello there</v>

2
00:01:02.500 --> 00:01:04.000
<v Sam Chen>Reply</v>
"""
        out = stp.parse_vtt(vtt)
        self.assertIn("**Alex Rivera** [0:03]: Hello there", out)
        self.assertIn("**Sam Chen** [1:02]: Reply", out)


class ExtractVttShellTests(unittest.TestCase):
    def test_extract_document_vtt(self):
        import subprocess

        script = WORKBENCH / "scripts" / "extract_document.sh"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.vtt"
            p.write_text(
                "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>Hi</v>\n",
                encoding="utf-8",
            )
            r = subprocess.run(
                ["bash", str(script), str(p)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            out = Path(r.stdout.strip())
            self.assertTrue(out.is_file())
            body = out.read_text(encoding="utf-8")
            self.assertIn("**A**", body)
            self.assertIn("Hi", body)


class ClipperStaticTests(unittest.TestCase):
    def test_manifest_v06(self):
        text = (CLIPPER / "manifest.json").read_text(encoding="utf-8")
        self.assertIn('"0.6.0"', text)

    def test_background_has_slow_scroll_and_speaker_parse(self):
        bg = (CLIPPER / "background.js").read_text(encoding="utf-8")
        self.assertIn("0.35", bg)
        self.assertIn("waitForSettle", bg)
        self.assertIn("parseSpeakerLabel", bg)
        self.assertIn("DURATION_RE", bg)
        self.assertIn("missing_posinset", bg)
        self.assertIn("speakers:", bg)
        self.assertIn("clientHeight * 0.35", bg)
        self.assertIn("incomplete = !!(setSize && missing.length > 0)", bg)
        # Primary advance is step scroll; scrollIntoView only in optional gap fill
        self.assertIn("async function slowScrollCapture", bg)
        self.assertIn("Optional full-height fallback", bg)

    def test_fixture_has_no_authtoken(self):
        html = FIXTURE.read_text(encoding="utf-8")
        self.assertNotIn("AuthToken", html)
        self.assertIn('aria-setsize="278"', html)
        self.assertIn('id="entry-21"', html)

    def test_gate_in_workflows(self):
        for name in ("process-inbox.md", "meeting-closeout.md"):
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            self.assertIn("incomplete: true", text)
            self.assertIn("[NEEDS INPUT]", text)


if __name__ == "__main__":
    unittest.main()
