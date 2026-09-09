#!/usr/bin/env bash
# extract_document.sh — converts a dropped file in inbox/documents/ to plain text
# so Claude can read it reliably. Office binary formats (.docx, .pptx, .xlsx) don't
# extract cleanly through a generic file read; this handles the conversion once.
#
# Usage: scripts/extract_document.sh inbox/documents/some-file.docx
# Outputs: same name, .txt, in the same folder.
#
# Uses tools already built into macOS or trivially installable:
#   .docx, .doc, .rtf  -> `textutil` (built into macOS, no install needed)
#   .pdf               -> `pdftotext` (brew install poppler if missing)
#   .pptx              -> textutil handles some; otherwise ask Claude to use
#                         python-docx/python-pptx (pip install --user python-pptx)
#   .xlsx              -> prefer re-exporting as .csv from Excel/Numbers directly;
#                         if that's not possible, python's openpyxl works too
#
# FIRST-TIME SETUP: this is a stub. Open in Cursor and ask Claude to fill in the
# case statement below for whichever formats you actually encounter first —
# no need to build all of them before you've dropped a real file to test with.

set -e
FILE="$1"
if [ -z "$FILE" ]; then
  echo "Usage: $0 <path-to-file>"
  exit 1
fi

echo "extract_document.sh is a stub — ask Claude (Cursor or Claude Code) to"
echo "implement the conversion for: $FILE"
echo "based on its extension, using textutil/pdftotext/python-docx as noted above."
exit 1
