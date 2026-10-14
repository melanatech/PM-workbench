#!/usr/bin/env python3
"""Neutral citations, local renderers, and the external-artifact hook.

The fixture company in this file is Lumenly. Kit code stays domain-neutral.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / ".claude" / "hooks"))

import check_external_artifact as external  # noqa: E402
import publish  # noqa: E402
import render_template  # noqa: E402

HOOK = KIT / ".claude" / "hooks" / "check_external_artifact.py"
LINK_HOOK = KIT / ".claude" / "hooks" / "check_md_links.py"
MEETING = "archive/meetings/2026-10-13-product-sync.md"
BRIEF = "outputs/briefs/q4-plan.md"
JIRA_URL = "https://tracker.example/browse/REPORT-2222"
WIKI_URL = "https://wiki.example/wiki/spaces/T/pages/1/Launch+notes"
DASHBOARD_URL = "https://dashboard.example/activation"

NEUTRAL = (
    "Product sync, 2026-10-13 (meeting notes)",
    "Uploaded document: Q4 planning deck.pdf",
    "Jira REPORT-2222",
    "Confluence: Launch notes",
    "Slack #planning, 2026-10-12",
    "Internal dashboard: Activation, as of 2026-10-01",
    "unverified",
    "early signal",
    "Ship the export in October.",
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_workspace(root: Path, audiences: str | None = None) -> None:
    meeting = root / MEETING
    meeting.parent.mkdir(parents=True, exist_ok=True)
    meeting.write_text("# Product sync\n\nLumenly planning notes.\n", encoding="utf-8")
    brief = root / BRIEF
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("# Q4 plan\n\nScope.\n", encoding="utf-8")
    (root / "inbox" / "documents").mkdir(parents=True, exist_ok=True)
    (root / "inbox" / "documents" / "Q4 planning deck.pdf").write_bytes(b"%PDF-1.1\n")

    write_csv(
        root / "registers" / "decisions.csv",
        ["id", "date", "decision", "made_by", "source_link", "affects"],
        [
            {
                "id": "DEC-015",
                "date": "2026-10-13",
                "decision": "Ship the export in October",
                "made_by": "Alex",
                "source_link": MEETING,
                "affects": "export",
            },
            {
                "id": "DEC-016",
                "date": "2026-10-12",
                "decision": "Track the launch item",
                "made_by": "Alex",
                "source_link": JIRA_URL,
                "affects": "export",
            },
        ],
    )
    write_csv(
        root / "registers" / "commitments.csv",
        ["id", "description", "owner", "due_date", "audience", "source", "status", "last_updated"],
        [{
            "id": "COM-003",
            "description": "Send the recap",
            "owner": "Alex",
            "due_date": "2026-10-20",
            "audience": "leadership",
            "source": MEETING,
            "status": "open",
            "last_updated": "2026-10-13",
        }],
    )
    write_csv(
        root / "registers" / "risks.csv",
        ["id", "date_raised", "risk", "severity", "mitigation", "status", "source"],
        [{
            "id": "RISK-001",
            "date_raised": "2026-10-13",
            "risk": "Date may slip",
            "severity": "medium",
            "mitigation": "Check again Friday",
            "status": "open",
            "source": MEETING,
        }],
    )
    evidence_fields = [
        "evidence_id", "capture_date", "source_date", "source_app", "source_url",
        "account", "user_role", "segment", "workflow_stage", "exact_observation",
        "interpreted_problem", "workaround", "severity", "frequency_signal",
        "business_relevance", "related_feature", "related_okr", "evidence_type", "confidence",
    ]
    blank = {name: "" for name in evidence_fields}
    rows = []
    for ident, app, url, source_date, observation in (
        ("EV-003", "upload", "inbox/documents/Q4 planning deck.pdf", "2026-10-11", "The deck shows the date."),
        ("EV-004", "confluence", WIKI_URL, "2026-10-10", "The page records the decision."),
        ("EV-005", "slack", "slack:#planning", "2026-10-12", "The channel agreed."),
    ):
        row = dict(blank)
        row.update({
            "evidence_id": ident,
            "capture_date": "2026-10-14",
            "source_date": source_date,
            "source_app": app,
            "source_url": url,
            "exact_observation": observation,
            "evidence_type": "reported",
            "confidence": "medium",
        })
        rows.append(row)
    write_csv(root / "registers" / "evidence.csv", evidence_fields, rows)
    write_csv(
        root / "registers" / "initiatives.csv",
        ["id", "name", "stage", "prd", "prototype", "experiment", "launch",
         "related_okr", "related_decisions", "related_risks", "last_updated", "notes"],
        [{
            "id": "INIT-001",
            "name": "Export",
            "stage": "discovery",
            "prd": BRIEF,
            "prototype": "",
            "experiment": "",
            "launch": "",
            "related_okr": "",
            "related_decisions": "DEC-015",
            "related_risks": "",
            "last_updated": "2026-10-14",
            "notes": "",
        }],
    )
    write_csv(
        root / "registers" / "todos.csv",
        ["id", "description", "owner", "due_date", "priority", "status", "initiative",
         "blocks", "links", "origin", "source", "created", "last_updated", "note"],
        [{
            "id": "TODO-004",
            "description": "Read the brief",
            "owner": "me",
            "due_date": "",
            "priority": "normal",
            "status": "open",
            "initiative": "INIT-001",
            "blocks": "",
            "links": "",
            "origin": "chat",
            "source": BRIEF,
            "created": "2026-10-14",
            "last_updated": "2026-10-14",
            "note": "",
        }],
    )
    write_csv(
        root / "state" / "okr-history.csv",
        ["metric", "value", "as_of_date", "retrieved_date", "timeframe", "filters",
         "delta", "chart", "notes", "source"],
        [{
            "metric": "Activation",
            "value": "10",
            "as_of_date": "2026-10-01",
            "retrieved_date": "2026-10-02",
            "timeframe": "",
            "filters": "",
            "delta": "",
            "chart": "",
            "notes": "displayed",
            "source": DASHBOARD_URL,
        }],
    )
    audiences_path = root / "reference" / "context" / "audiences.md"
    audiences_path.parent.mkdir(parents=True, exist_ok=True)
    if audiences is None:
        audiences = (
            "# Audiences\n\n"
            "| Output | Audience | Cares about | Format | Channel | Systems they can access | Source |\n"
            "|---|---|---|---|---|---|---|\n"
            "| weekly update | leadership | outcomes | one page | mail | tracker and wiki and dashboard | notes |\n"
        )
    audiences_path.write_text(audiences, encoding="utf-8")


DRAFT = """---
audience: internal
formats: [md, html, docx, confluence, slack]
output: weekly update
---

# Weekly update

Ship the export in October. DEC-015

The deck says so. EV-003

Tracker: DEC-016

Wiki: EV-004

Chat: EV-005

Activation is metric:Activation.

See outputs/briefs/q4-plan.md.

Also INIT-001 and TODO-004 and COM-003 and RISK-001.

The result is [hypothesis: early signal] and [hypothesis] and [external::training].
"""


def _write_aliases(root: Path, rows: list[tuple]) -> None:
    """Write an alias table. All-None treatments keep the old three-column shape."""
    lines = ["# Aliases", ""]
    wide = any(row[3] is not None or row[4] is not None for row in rows)
    if wide:
        lines.append("| Phrase | Path | Meaning | external_treatment | external_value |")
        lines.append("|---|---|---|---|---|")
    else:
        lines.append("| Phrase | Path | Meaning |")
        lines.append("|---|---|---|")
    for phrase, path, meaning, treatment, value in rows:
        if treatment is None and value is None and not wide:
            lines.append(f"| {phrase} | {path} | {meaning} |")
        else:
            lines.append(f"| {phrase} | {path} | {meaning} | {treatment or ''} | {value or ''} |")
    dest = root / "reference" / "context" / "workspace-aliases.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_hook(hook: Path, file_path: Path, project: Path) -> subprocess.CompletedProcess:
    payload = {"tool_input": {"file_path": str(file_path)}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-publish-"))
        build_workspace(self.tmp)
        self.workspace = publish.Workspace.load(self.tmp)
        self.linked = publish.Access(jira=True, confluence=True, dashboard=True)
        self.plain = publish.Access()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_meeting_decision_becomes_name_and_date(self):
        citation = self.workspace.resolve_id("DEC-015", self.plain)
        self.assertEqual(citation.text, "Product sync, 2026-10-13 (meeting notes)")
        self.assertIsNone(citation.url)

    def test_commitment_and_risk_use_the_meeting_behind_them(self):
        for ident in ("COM-003", "RISK-001"):
            citation = self.workspace.resolve_id(ident, self.plain)
            self.assertEqual(citation.text, "Product sync, 2026-10-13 (meeting notes)", ident)

    def test_uploaded_document_uses_the_file_name(self):
        citation = self.workspace.resolve_id("EV-003", self.plain)
        self.assertEqual(citation.text, "Uploaded document: Q4 planning deck.pdf")
        self.assertNotIn("inbox/", citation.text)

    def test_jira_links_only_when_the_audience_has_the_tracker(self):
        linked = self.workspace.resolve_id("DEC-016", self.linked)
        plain = self.workspace.resolve_id("DEC-016", self.plain)
        self.assertEqual(linked.text, "Jira REPORT-2222")
        self.assertEqual(linked.url, JIRA_URL)
        self.assertEqual(plain.text, "Jira REPORT-2222")
        self.assertIsNone(plain.url)

    def test_confluence_uses_the_page_title(self):
        linked = self.workspace.resolve_id("EV-004", self.linked)
        plain = self.workspace.resolve_id("EV-004", self.plain)
        self.assertEqual(linked.text, "Confluence: Launch notes")
        self.assertEqual(linked.url, WIKI_URL)
        self.assertIsNone(plain.url)

    def test_slack_uses_channel_and_date(self):
        citation = self.workspace.resolve_id("EV-005", self.plain)
        self.assertEqual(citation.text, "Slack #planning, 2026-10-12")
        self.assertIsNone(citation.url)

    def test_metric_uses_dashboard_name_and_as_of(self):
        linked = self.workspace.resolve_metric("Activation", self.linked)
        plain = self.workspace.resolve_metric("Activation", self.plain)
        self.assertEqual(linked.text, "Internal dashboard: Activation, as of 2026-10-01")
        self.assertEqual(linked.url, DASHBOARD_URL)
        self.assertIsNone(plain.url)

    def test_workspace_path_becomes_the_document_title(self):
        text, notes = publish.neutralize(f"See {BRIEF}.", self.workspace, self.plain)
        self.assertNotIn("outputs/", text)
        self.assertIn("Q4 plan", text)
        self.assertEqual(notes[0].citation.text, "Q4 plan")

    def test_hypothesis_and_training_tags_become_inline_wording(self):
        text, notes = publish.neutralize(
            "This is [hypothesis: early signal] and [hypothesis] plus [external::training].",
            self.workspace,
            self.plain,
        )
        self.assertIn("early signal", text)
        self.assertIn("unverified", text)
        self.assertNotIn("[hypothesis", text)
        self.assertNotIn("[external::training]", text)
        self.assertEqual(notes, [])

    def test_missing_register_id_fails_loudly(self):
        with self.assertRaises(publish.PublishError) as caught:
            self.workspace.resolve_id("DEC-999", self.plain)
        self.assertIn("DEC-999", str(caught.exception))
        self.assertIn("not in registers", str(caught.exception))

    def test_register_id_with_no_source_fails_loudly(self):
        path = self.tmp / "registers" / "decisions.csv"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("DEC-017,2026-10-14,No source,Alex,,export\n")
        workspace = publish.Workspace.load(self.tmp)
        with self.assertRaises(publish.PublishError) as caught:
            workspace.resolve_id("DEC-017", self.plain)
        self.assertIn("DEC-017", str(caught.exception))
        self.assertIn("no source", str(caught.exception))

    def test_unknown_metric_fails_loudly(self):
        with self.assertRaises(publish.PublishError) as caught:
            self.workspace.resolve_metric("NotAMetric", self.plain)
        self.assertIn("NotAMetric", str(caught.exception))

    def test_template_audiences_grant_no_links(self):
        text = (KIT / "reference" / "context" / "audiences.example.md").read_text(encoding="utf-8")
        access = publish.load_access(self._write_audiences(text), "weekly update")
        self.assertFalse(access.jira)
        self.assertIn("template", access.note)

    def test_filled_audience_row_grants_named_systems(self):
        access = publish.load_access(self.tmp / "reference" / "context" / "audiences.md", "weekly update")
        self.assertTrue(access.jira)
        self.assertTrue(access.confluence)
        self.assertTrue(access.dashboard)
        self.assertFalse(access.slack)

    def _write_audiences(self, text: str) -> Path:
        path = self.tmp / "reference" / "context" / "audiences-template.md"
        path.write_text(text, encoding="utf-8")
        return path


class PublishFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-publish-"))
        build_workspace(self.tmp)
        self.draft = self.tmp / "outputs" / "weekly" / "2026-10-14-update.md"
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.draft.write_text(DRAFT, encoding="utf-8")
        self.before = self.draft.read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_publish_writes_neutral_copies_and_keeps_the_internal_draft(self):
        result = publish.publish_file(self.draft, self.tmp)
        self.assertEqual(self.draft.read_text(encoding="utf-8"), self.before)
        external = (self.tmp / "outputs" / "external" / "2026-10-14-update.md").read_text(encoding="utf-8")
        self.assertIn("audience: external", external)
        self.assertIn("Ship the export in October.", external)
        for citation in NEUTRAL[:6]:
            self.assertIn(citation, external, citation)
        self.assertIn("early signal", external)
        self.assertIn("unverified", external)
        for label in ("DEC-015", "DEC-016", "EV-003", "EV-004", "EV-005", "INIT-001", "TODO-004", "COM-003", "RISK-001"):
            self.assertNotIn(label, external, label)
        self.assertNotIn("outputs/", external)
        self.assertNotIn("inbox/", external)
        self.assertNotIn("[hypothesis", external)
        self.assertNotIn("[external::training]", external)
        self.assertIn(f"[Jira REPORT-2222]({JIRA_URL})", external)
        self.assertIn(f"[Confluence: Launch notes]({WIKI_URL})", external)
        self.assertIn(f"[Internal dashboard: Activation, as of 2026-10-01]({DASHBOARD_URL})", external)
        sidecar = (self.draft.parent / "2026-10-14-update.sources.md").read_text(encoding="utf-8")
        self.assertIn("DEC-015", sidecar)
        self.assertIn("Product sync, 2026-10-13 (meeting notes)", sidecar)
        self.assertNotIn(self.tmp.as_posix(), external)
        names = {path.name for path in result.files}
        self.assertIn("2026-10-14-update.html", names)
        self.assertIn("2026-10-14-update.docx", names)
        self.assertIn("2026-10-14-update.confluence.xml", names)
        self.assertIn("2026-10-14-update.slack.md", names)

    def test_each_format_renders(self):
        publish.publish_file(self.draft, self.tmp)
        out = self.tmp / "outputs" / "external"
        html_text = (out / "2026-10-14-update.html").read_text(encoding="utf-8")
        self.assertIn("<style>", html_text)
        self.assertNotIn('rel="stylesheet"', html_text)
        self.assertIn("Product sync, 2026-10-13 (meeting notes)", html_text)
        self.assertNotIn("DEC-015", html_text)
        confluence = (out / "2026-10-14-update.confluence.xml").read_text(encoding="utf-8")
        self.assertIn("<p>", confluence)
        self.assertIn("Confluence: Launch notes", confluence)
        self.assertNotIn("EV-004", confluence)
        slack = (out / "2026-10-14-update.slack.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(slack), render_template.SLACK_LIMIT)
        self.assertIn("Slack #planning, 2026-10-12", slack)
        self.assertIn("*Weekly update*", slack)
        self.assertNotIn("EV-005", slack)
        docx = out / "2026-10-14-update.docx"
        with zipfile.ZipFile(docx) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            document = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Ship the export in October.", document)
        self.assertIn("Product sync, 2026-10-13 (meeting notes)", document)
        self.assertNotIn("DEC-015", document)

    def test_needs_input_blocks_publishing_and_writes_nothing(self):
        self.draft.write_text("Owner is [NEEDS INPUT: owner].\n", encoding="utf-8")
        with self.assertRaises(publish.NeedsInputError):
            publish.publish_file(self.draft, self.tmp, formats=["md"])
        self.assertFalse((self.tmp / "outputs" / "external").exists())
        self.assertEqual(list(self.tmp.rglob("*.sources.md")), [])

    def test_unresolvable_id_writes_nothing(self):
        self.draft.write_text("We agreed DEC-999.\n", encoding="utf-8")
        with self.assertRaises(publish.PublishError) as caught:
            publish.publish_file(self.draft, self.tmp, formats=["md"])
        self.assertIn("DEC-999", str(caught.exception))
        self.assertFalse((self.tmp / "outputs" / "external").exists())

    def test_cli_exit_codes(self):
        blocked = self.tmp / "outputs" / "weekly" / "blocked.md"
        blocked.write_text("Still [NEEDS INPUT].\n", encoding="utf-8")
        missing = self.tmp / "outputs" / "weekly" / "missing.md"
        missing.write_text("See DEC-999.\n", encoding="utf-8")
        script = KIT / "scripts" / "publish.py"
        needs = subprocess.run(
            [sys.executable, str(script), str(blocked), "--root", str(self.tmp), "--formats", "md"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(needs.returncode, 2, needs.stderr)
        self.assertIn("NEEDS INPUT", needs.stderr)
        unknown = subprocess.run(
            [sys.executable, str(script), str(missing), "--root", str(self.tmp), "--formats", "md"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(unknown.returncode, 1, unknown.stderr)
        self.assertIn("DEC-999", unknown.stderr)

    def test_alias_phrase_blocks_the_publish(self):
        aliases = self.tmp / "reference" / "context" / "workspace-aliases.md"
        aliases.write_text(
            "# Aliases\n\n| Phrase | Path | Meaning |\n|---|---|---|\n| lumen scorecard | somewhere | internal name |\n",
            encoding="utf-8",
        )
        self.draft.write_text("# Update\n\nSee the lumen scorecard.\n", encoding="utf-8")
        with self.assertRaises(publish.PublishError) as caught:
            publish.publish_file(self.draft, self.tmp, formats=["md"])
        message = str(caught.exception)
        self.assertIn("lumen scorecard", message)
        self.assertIn("external_treatment", message)
        self.assertFalse((self.tmp / "outputs" / "external").exists())

    def test_alias_treatments_expand_preserve_neutralize_and_block(self):
        _write_aliases(
            self.tmp,
            [
                ("events digest / instrumentation digests", "outputs/daily/", "process label", "neutralize", "prior analysis of analytics events"),
                ("weekly scorecard", "outputs/weekly/", "leadership drafts", "expand", "weekly leadership update"),
                ("scorecard", "outputs/weekly/", "shorter name", "expand", "SHORT"),
                ("glossary", "reference/context/glossary.md", "plain word", "preserve", ""),
                ("schema codename", "outputs/weekly/", "confidential", "internal_only", ""),
                ("unclassified label", "outputs/weekly/", "not yet classified", "", "[NEEDS INPUT]"),
                ("bare shorthand", "outputs/weekly/", "old three-column shape", None, None),
            ],
        )
        self.draft.write_text(
            "# Update\n\nSee the weekly scorecard, the events digest, and the glossary.\n",
            encoding="utf-8",
        )
        result = publish.publish_file(self.draft, self.tmp, formats=["md"])
        self.assertIn("weekly leadership update", result.body)
        self.assertIn("prior analysis of analytics events", result.body)
        self.assertIn("glossary", result.body)
        self.assertNotIn("weekly scorecard", result.body)
        self.assertNotIn("events digest", result.body)
        self.assertNotIn("SHORT", result.body)

        blocked = {
            "schema codename": "internal_only",
            "unclassified label": "external_treatment",
            "bare shorthand": "external_treatment",
        }
        for phrase, expected in blocked.items():
            self.draft.write_text(f"# Update\n\nSee the {phrase}.\n", encoding="utf-8")
            with self.assertRaises(publish.PublishError) as caught:
                publish.publish_file(self.draft, self.tmp, formats=["md"])
            message = str(caught.exception)
            self.assertIn(phrase, message, phrase)
            self.assertIn(expected, message, phrase)
        self.assertIn("weekly leadership update", (self.tmp / "outputs" / "external" / "2026-10-14-update.md").read_text(encoding="utf-8"))

    def test_expand_without_a_value_blocks(self):
        _write_aliases(
            self.tmp,
            [("weekly scorecard", "outputs/weekly/", "leadership drafts", "expand", "")],
        )
        self.draft.write_text("# Update\n\nSee the weekly scorecard.\n", encoding="utf-8")
        with self.assertRaises(publish.PublishError) as caught:
            publish.publish_file(self.draft, self.tmp, formats=["md"])
        self.assertIn("weekly scorecard", str(caught.exception))
        self.assertIn("external_value", str(caught.exception))
        self.assertFalse((self.tmp / "outputs" / "external" / "2026-10-14-update.md").exists())

    def test_preserve_is_not_blanket_blocked(self):
        _write_aliases(
            self.tmp,
            [
                ("glossary", "reference/context/glossary.md", "plain word", "preserve", ""),
                ("lumen scorecard", "somewhere", "old row", None, None),
            ],
        )
        phrases = external.load_alias_phrases(self.tmp)
        self.assertIn("lumen scorecard", phrases)
        self.assertNotIn("glossary", phrases)
        self.draft.write_text("# Update\n\nUse the glossary.\n", encoding="utf-8")
        result = publish.publish_file(self.draft, self.tmp, formats=["md"])
        self.assertIn("glossary", result.body)
        self.assertEqual(external.find_banned(result.body, phrases), [])

    def test_example_documents_every_treatment_and_preflight_keeps_phrases(self):
        import context_preflight

        example = KIT / "reference" / "context" / "workspace-aliases.example.md"
        text = example.read_text(encoding="utf-8")
        for token in ("Orders", "Payments", "Cube"):
            self.assertNotIn(token, text)
        aliases = external.load_alias_file(example)
        by_phrase = {phrase: alias for alias in aliases for phrase in alias.phrases}
        self.assertEqual(by_phrase["events digest"].treatment, "neutralize")
        self.assertEqual(by_phrase["instrumentation digests"].treatment, "neutralize")
        self.assertEqual(by_phrase["instrumentation digests"].external_value, "prior analysis of analytics events")
        self.assertEqual(by_phrase["weekly scorecard"].treatment, "expand")
        self.assertEqual(by_phrase["weekly scorecard"].external_value, "weekly leadership update")
        self.assertEqual(by_phrase["glossary"].treatment, "preserve")
        self.assertEqual(by_phrase["schema codename"].treatment, "internal_only")
        self.assertEqual(by_phrase["unclassified label"].treatment, "")
        self.assertNotIn("internal_only", by_phrase)
        rows = context_preflight._load_aliases(KIT)
        phrases = " ".join(row["phrase"] for row in rows)
        self.assertIn("weekly scorecard", phrases)
        self.assertIn("glossary", phrases)
        self.assertNotIn("Treatment", phrases)


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-render-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_docx_is_a_zip_with_document_xml(self):
        dest = self.tmp / "note.docx"
        blocks = render_template.markdown_to_blocks(
            "# Hello\n\nA paragraph.\n\n- bullet item\n\n"
            "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
            "[Example](https://example.com)\n"
        )
        render_template.blocks_to_docx(blocks, dest)
        with zipfile.ZipFile(dest) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            document = archive.read("word/document.xml").decode("utf-8")
            rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
        self.assertIn("Hello", document)
        self.assertIn("bullet item", document)
        self.assertIn(">1<", document)
        self.assertIn("https://example.com", rels)

    def test_company_styles_xml_is_copied(self):
        template = self.tmp / "brand.docx"
        with zipfile.ZipFile(template, "w") as archive:
            archive.writestr("word/styles.xml", "<w:styles>COMPANY_STYLE_MARKER</w:styles>")
        dest = self.tmp / "out.docx"
        render_template.blocks_to_docx(
            render_template.markdown_to_blocks("# Title\n"),
            dest,
            styles_docx=template,
        )
        with zipfile.ZipFile(dest) as archive:
            styles = archive.read("word/styles.xml").decode("utf-8")
        self.assertIn("COMPANY_STYLE_MARKER", styles)

    def test_slack_parts_stay_within_the_limit(self):
        paragraph = "word " * 2000
        parts = render_template.blocks_to_slack(render_template.markdown_to_blocks(paragraph))
        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), render_template.SLACK_LIMIT)
        self.assertIn("word", "".join(parts))

    def test_xlsx_is_rejected(self):
        template = self.tmp / "book.xlsx"
        template.write_bytes(b"")
        context = self.tmp / "context.json"
        context.write_text('{"markdown": "# Hi"}', encoding="utf-8")
        code = render_template.main([str(template), str(context), str(self.tmp / "out.xlsx")])
        self.assertEqual(code, 1)


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-hook-"))
        (self.tmp / "registers").mkdir()
        (self.tmp / "registers" / "risks.csv").write_text("id\n", encoding="utf-8")
        (self.tmp / "outputs" / "external").mkdir(parents=True)
        (self.tmp / "outputs" / "weekly").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_banned_patterns_and_neutral_citations(self):
        phrases = ["lumen scorecard"]
        for line in NEUTRAL:
            self.assertEqual(external.find_banned(line, phrases), [], line)
        self.assertEqual(external.find_banned("See DEC-015 today.", []), ["DEC-015"])
        self.assertEqual(external.find_banned("See COM-003.", []), ["COM-003"])
        self.assertEqual(external.find_banned("See RISK-001.", []), ["RISK-001"])
        self.assertEqual(external.find_banned("See EV-003.", []), ["EV-003"])
        self.assertEqual(external.find_banned("See INIT-001.", []), ["INIT-001"])
        self.assertEqual(external.find_banned("See TODO-004.", []), ["TODO-004"])
        paths = external.find_banned("See outputs/weekly/note.md for it.", [])
        self.assertTrue(any(item.startswith("outputs/") for item in paths), paths)
        users = external.find_banned("Open /Users/nlee1/pm-live/note.md now.", [])
        self.assertTrue(any(item.startswith("/Users/") for item in users), users)
        self.assertTrue(external.find_banned("Gap [NEEDS INPUT: owner].", []))
        self.assertTrue(external.find_banned("Gap [NEEDS INPUT].", []))
        self.assertTrue(external.find_banned("Maybe [hypothesis: early signal].", []))
        self.assertTrue(external.find_banned("Model [external::training].", []))
        self.assertEqual(
            external.find_banned("See the lumen scorecard today.", phrases),
            ["lumen scorecard"],
        )

    def test_template_alias_file_adds_no_codenames(self):
        path = self.tmp / "reference" / "context" / "workspace-aliases.md"
        path.parent.mkdir(parents=True)
        path.write_text("status: template\n\n| Phrase | Path |\n|---|---|\n| glossary | somewhere |\n", encoding="utf-8")
        self.assertEqual(external.load_alias_phrases(self.tmp), [])
        self.assertEqual(external.find_banned("Use the glossary.", external.load_alias_phrases(self.tmp)), [])

    def test_hook_blocks_each_pattern_and_passes_neutral_text(self):
        neutral = self.tmp / "outputs" / "external" / "ok.md"
        neutral.write_text("---\naudience: external\n---\n\n" + "\n".join(NEUTRAL) + "\n", encoding="utf-8")
        passed = run_hook(HOOK, neutral, self.tmp)
        self.assertEqual(passed.returncode, 0, passed.stderr)

        cases = {
            "id.md": "DEC-015",
            "path.md": "outputs/weekly/note.md",
            "home.md": "/Users/nlee1/pm-live/note.md",
            "needs.md": "[NEEDS INPUT: owner]",
            "hypothesis.md": "[hypothesis: early signal]",
            "training.md": "[external::training]",
        }
        for name, body in cases.items():
            path = self.tmp / "outputs" / "external" / name
            path.write_text(f"---\naudience: external\n---\n\n{body}\n", encoding="utf-8")
            result = run_hook(HOOK, path, self.tmp)
            self.assertEqual(result.returncode, 2, name + result.stderr)
            self.assertIn(body[:12], result.stderr)

        aliases = self.tmp / "reference" / "context" / "workspace-aliases.md"
        aliases.parent.mkdir(parents=True, exist_ok=True)
        aliases.write_text(
            "| Phrase | Path | Meaning |\n|---|---|---|\n| lumen scorecard | x | internal |\n",
            encoding="utf-8",
        )
        coded = self.tmp / "outputs" / "external" / "code.md"
        coded.write_text("---\naudience: external\n---\n\nSee the lumen scorecard.\n", encoding="utf-8")
        coded_result = run_hook(HOOK, coded, self.tmp)
        self.assertEqual(coded_result.returncode, 2, coded_result.stderr)
        self.assertIn("lumen scorecard", coded_result.stderr)
        self.assertIn("external_treatment", coded_result.stderr)

    def test_hook_follows_alias_treatment(self):
        _write_aliases(
            self.tmp,
            [
                ("weekly scorecard", "outputs/weekly/", "leadership drafts", "expand", "weekly leadership update"),
                ("events digest", "outputs/daily/", "process label", "neutralize", "prior analysis of analytics events"),
                ("glossary", "reference/context/glossary.md", "plain word", "preserve", ""),
                ("schema codename", "outputs/weekly/", "confidential", "internal_only", ""),
                ("unclassified label", "outputs/weekly/", "not yet classified", "", ""),
            ],
        )
        passed = self.tmp / "outputs" / "external" / "ready.md"
        passed.write_text(
            "---\naudience: external\n---\n\n"
            "The weekly leadership update cites the prior analysis of analytics events and the glossary.\n",
            encoding="utf-8",
        )
        ok = run_hook(HOOK, passed, self.tmp)
        self.assertEqual(ok.returncode, 0, ok.stderr)

        raw_expand = self.tmp / "outputs" / "external" / "raw-expand.md"
        raw_expand.write_text("---\naudience: external\n---\n\nSee the weekly scorecard.\n", encoding="utf-8")
        expand_result = run_hook(HOOK, raw_expand, self.tmp)
        self.assertEqual(expand_result.returncode, 2, expand_result.stderr)
        self.assertIn("expand", expand_result.stderr)

        for name, phrase, marker in (
            ("secret.md", "schema codename", "internal_only"),
            ("open.md", "unclassified label", "external_treatment"),
        ):
            path = self.tmp / "outputs" / "external" / name
            path.write_text(f"---\naudience: external\n---\n\nSee the {phrase}.\n", encoding="utf-8")
            result = run_hook(HOOK, path, self.tmp)
            self.assertEqual(result.returncode, 2, name + result.stderr)
            self.assertIn(phrase, result.stderr)
            self.assertIn(marker, result.stderr)

    def test_hook_scans_docx_under_external(self):
        dest = self.tmp / "outputs" / "external" / "bad.docx"
        render_template.blocks_to_docx(
            render_template.markdown_to_blocks("Still citing DEC-015."),
            dest,
        )
        blocked = run_hook(HOOK, dest, self.tmp)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("DEC-015", blocked.stderr)
        good = self.tmp / "outputs" / "external" / "good.docx"
        render_template.blocks_to_docx(
            render_template.markdown_to_blocks("Product sync, 2026-10-13 (meeting notes)."),
            good,
        )
        passed = run_hook(HOOK, good, self.tmp)
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_link_hook_skips_external_audience_and_external_dir(self):
        internal = self.tmp / "outputs" / "weekly" / "internal.md"
        internal.write_text("See registers/risks.csv for details.\n", encoding="utf-8")
        blocked = run_hook(LINK_HOOK, internal, self.tmp)
        self.assertEqual(blocked.returncode, 2, blocked.stderr)

        marked = self.tmp / "outputs" / "weekly" / "marked.md"
        marked.write_text(
            "---\naudience: external\n---\n\nSee registers/risks.csv for details.\n",
            encoding="utf-8",
        )
        skipped = run_hook(LINK_HOOK, marked, self.tmp)
        self.assertEqual(skipped.returncode, 0, skipped.stderr)

        external_dir = self.tmp / "outputs" / "external" / "copy.md"
        external_dir.write_text("See registers/risks.csv for details.\n", encoding="utf-8")
        skipped_dir = run_hook(LINK_HOOK, external_dir, self.tmp)
        self.assertEqual(skipped_dir.returncode, 0, skipped_dir.stderr)
        still_blocked = run_hook(HOOK, external_dir, self.tmp)
        self.assertEqual(still_blocked.returncode, 2, still_blocked.stderr)

    def test_internal_file_is_not_an_external_artifact(self):
        path = self.tmp / "outputs" / "weekly" / "internal.md"
        path.write_text("DEC-015 stays in the internal draft.\n", encoding="utf-8")
        result = run_hook(HOOK, path, self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)


class WiringTests(unittest.TestCase):
    def test_reviewer_model_is_haiku(self):
        text = (KIT / ".claude" / "agents" / "external-readiness-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("model: haiku", text)
        self.assertIn("audience line", text)

    def test_protocol_publish_steps_name_roadmap_build(self):
        text = (KIT / ".claude" / "workflows" / "_protocol.md").read_text(encoding="utf-8")
        self.assertIn("## Publish", text)
        self.assertIn("external-readiness-reviewer", text)
        self.assertIn("roadmap-build", text)
        self.assertIn("Tier 3", text)
        self.assertIn("external_treatment", text)
        self.assertIn("not banned as a set", text)

    def test_settings_register_the_external_hook(self):
        for name in ("settings.json", "settings.core.json", "settings.full.json"):
            text = (KIT / ".claude" / name).read_text(encoding="utf-8")
            self.assertIn("check_external_artifact.py", text, name)
            json.loads(text)


if __name__ == "__main__":
    unittest.main()
