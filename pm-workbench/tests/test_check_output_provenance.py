#!/usr/bin/env python3
"""Tests for .claude/hooks/check_output_provenance.py — register citation check."""
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
HOOK = WORKBENCH / ".claude" / "hooks" / "check_output_provenance.py"


class ProvenanceRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-prov-"))
        (self.tmp / "registers").mkdir()
        (self.tmp / "outputs").mkdir()
        (self.tmp / "state").mkdir()
        (self.tmp / "registers" / "commitments.csv").write_text(
            "id,description,owner,due_date,audience,source,status,last_updated\n"
            "COM-001,exists,me,2026-10-01,self,test,open,2026-10-01\n",
            encoding="utf-8",
        )
        (self.tmp / "registers" / "risks.csv").write_text(
            "id,date_raised,risk,severity,mitigation,status,source\n",
            encoding="utf-8",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_hook(self, file_path: Path):
        payload = {"tool_input": {"file_path": str(file_path)}}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)}
        return subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_register_citing_missing_com_fails(self):
        risks = self.tmp / "registers" / "risks.csv"
        risks.write_text(
            "id,date_raised,risk,severity,mitigation,status,source\n"
            'RISK-001,2026-10-12,board hygiene,medium,"Fix KEY-100 (COM-099)",open,test\n',
            encoding="utf-8",
        )
        r = self.run_hook(risks)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("COM-099", r.stderr)

    def test_register_citing_existing_com_passes(self):
        risks = self.tmp / "registers" / "risks.csv"
        risks.write_text(
            "id,date_raised,risk,severity,mitigation,status,source\n"
            'RISK-001,2026-10-12,board hygiene,medium,"Track via COM-001",open,test\n',
            encoding="utf-8",
        )
        r = self.run_hook(risks)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_new_row_own_id_not_flagged(self):
        """A brand-new RISK-050 row must not fail because RISK-050 isn't 'known' yet
        as a citation — its id column is excluded from the citation scan."""
        risks = self.tmp / "registers" / "risks.csv"
        risks.write_text(
            "id,date_raised,risk,severity,mitigation,status,source\n"
            "RISK-050,2026-10-13,new risk,low,none yet,open,test\n",
            encoding="utf-8",
        )
        r = self.run_hook(risks)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_context_md_citing_missing_fails(self):
        ctx = self.tmp / "reference" / "context"
        ctx.mkdir(parents=True)
        f = ctx / "assumptions-and-open-questions.md"
        f.write_text("- open: see COM-777 for the fix\n", encoding="utf-8")
        r = self.run_hook(f)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("COM-777", r.stderr)


if __name__ == "__main__":
    unittest.main()
