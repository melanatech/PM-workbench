"""Pattern-borrow deliverables: templates, provenance tags, workflow hooks, agent addenda."""
from pathlib import Path
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
TEMPLATES = WORKBENCH / "reference" / "templates"
AGENTS = WORKBENCH / ".claude" / "agents"
WORKFLOWS = WORKBENCH / ".claude" / "workflows"

PROVENANCE_AGENTS = [
    "eng-feasibility-reviewer.md",
    "design-ux-reviewer.md",
    "data-instrumentation-reviewer.md",
    "business-revenue-reviewer.md",
    "customer-facing-reviewer.md",
    "causal-reviewer.md",
    "instrumentation-reviewer.md",
    "ux-harm-reviewer.md",
    "business-value-reviewer.md",
    "ops-feasibility-reviewer.md",
    "results-integrity-reviewer.md",
    "prd-context-gatherer.md",
    "strategy-synthesizer.md",
    "discovery-source-reader.md",
    "competitive-capture-agent.md",
]

HYGIENE_FILES = [
    WORKBENCH / "CLAUDE.md",
    WORKFLOWS / "_protocol.md",
    WORKFLOWS / "prd-package.md",
    WORKFLOWS / "meeting-prep.md",
    WORKBENCH / ".claude" / "skills" / "prototype-build" / "SKILL.md",
    TEMPLATES / "pm-lifecycle-experiment.md",
    TEMPLATES / "prototype-readiness-checklist.md",
    TEMPLATES / "stakeholder-lenses.md",
]

FORBIDDEN = (
    "gdcorp" + "-commerce",
    "pm-" + "hub",
    "pag" + "rawal",
    "commerce-product" + ".int",
    "pm-ch-" + "mockup",
)


class PatternBorrowTests(unittest.TestCase):
    def test_lifecycle_experiment_template(self):
        path = TEMPLATES / "pm-lifecycle-experiment.md"
        text = path.read_text(encoding="utf-8")
        for h in ("## Hypothesis", "## Control baseline", "## Treatment", "## Metrics", "## Out of scope"):
            self.assertIn(h, text)

    def test_learning_entity_stubs(self):
        for name in ("initiative", "metric", "jtbd", "decision"):
            path = TEMPLATES / "learning-entity-stubs" / f"{name}.md"
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"type: {name}", text)
            self.assertIn("## Overview", text)
            self.assertIn("## Open questions", text)

    def test_prototype_readiness_checklist(self):
        text = (TEMPLATES / "prototype-readiness-checklist.md").read_text(encoding="utf-8")
        self.assertIn("## Dimensions", text)
        self.assertIn("## Scoring", text)
        self.assertIn("worst-score-wins", text)

    def test_stakeholder_lenses_template(self):
        text = (TEMPLATES / "stakeholder-lenses.md").read_text(encoding="utf-8")
        self.assertIn("| Role | Focus area | Primary lens | Watch for |", text)
        self.assertIn("[Role]", text)
        self.assertIn("CLAUDE.local", text)

    def test_claude_and_protocol_provenance_tags(self):
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        protocol = (WORKFLOWS / "_protocol.md").read_text(encoding="utf-8")
        for text in (claude, protocol):
            self.assertIn("[hypothesis:", text)
            self.assertIn("[external::training]", text)
            self.assertIn("assumptions-and-open-questions", text)

    def test_prototype_build_mentions_readiness_checklist(self):
        skill = (WORKBENCH / ".claude" / "skills" / "prototype-build" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("prototype-readiness-checklist", skill)

    def test_prd_and_meeting_prep_mention_lenses(self):
        prd = (WORKFLOWS / "prd-package.md").read_text(encoding="utf-8")
        prep = (WORKFLOWS / "meeting-prep.md").read_text(encoding="utf-8")
        self.assertIn("stakeholder-lenses", prd)
        self.assertIn("stakeholder-lenses", prep)

    def test_agents_have_provenance_tagging(self):
        for name in PROVENANCE_AGENTS:
            text = (AGENTS / name).read_text(encoding="utf-8")
            self.assertIn("## Provenance tagging", text, name)
            self.assertIn("[hypothesis:", text, name)
            self.assertIn("[external::training]", text, name)

    def test_new_user_has_no_docs_hub_section(self):
        setup = (WORKBENCH / "NEW-USER-SETUP.md").read_text(encoding="utf-8")
        self.assertNotIn("company PM docs hub", setup)
        self.assertNotIn("## 2b. Optional: company PM docs hub", setup)
        # Do not add a §2a-parallel docs-hub recipe
        self.assertNotRegex(setup, r"(?i)##\s+\d+\w*\.\s+.*\bdocs hub\b")

    def test_hygiene_no_company_strings_in_touched_files(self):
        paths = list(HYGIENE_FILES)
        paths.extend(TEMPLATES / "learning-entity-stubs" / f"{n}.md" for n in ("initiative", "metric", "jtbd", "decision"))
        paths.extend(AGENTS / n for n in PROVENANCE_AGENTS)
        evolving = (WORKBENCH / "EVOLVING.md").read_text(encoding="utf-8")
        self.assertIn("pattern borrow", evolving.lower())
        # Check only the Pattern borrow changelog bullet (not older UI-base notes)
        borrow_line = next(
            (ln for ln in evolving.splitlines() if "Pattern borrow" in ln),
            "",
        )
        self.assertTrue(borrow_line, "missing Pattern borrow changelog line")
        for bad in FORBIDDEN:
            self.assertNotIn(bad, borrow_line, f"EVOLVING borrow line contains {bad}")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text, f"{path} contains {bad}")

    def test_evolving_documents_agency_skip_and_rejects(self):
        text = (WORKBENCH / "EVOLVING.md").read_text(encoding="utf-8")
        self.assertIn("Pattern borrow", text)
        self.assertIn("2026-10-06", text)
        lower = text.lower()
        self.assertIn("agency", lower)
        self.assertIn("skip", lower)
        self.assertIn("self-improv", lower)
        self.assertIn("docs-hub", lower)


if __name__ == "__main__":
    unittest.main()
