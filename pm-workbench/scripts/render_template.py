#!/usr/bin/env python3
"""
render_template.py — fills a formatted template with Claude-generated content.
Formatting lives in the template; this script only substitutes content.

Usage:
  python3 scripts/render_template.py <template> <context.json> <output>

.docx  -> docxtpl (pip install --user docxtpl). Context keys match {{ tags }}.
.xlsx  -> openpyxl: context keys match defined names (named cells/ranges);
          values written in place, workbook formatting preserved.
.pptx  -> python-pptx placeholder filling (text placeholders only — see the
          README's caveat; prefer draft-and-paste for design-heavy decks).

STUB: first time a command needs this, Claude implements the branch for the
format actually in use, per this docstring, then runs it. Until then commands
fall back to clean markdown output (CLAUDE.md rule 17 — never block on setup).
"""
import sys
print("render_template.py is a stub — Claude implements the needed branch on "
      "first real use, per the docstring. Falling back to markdown output is "
      "always acceptable in the meantime.")
sys.exit(1)
