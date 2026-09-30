#!/usr/bin/env bash
# STUB: this script currently exits without reading, converting, or writing a file.
# Use an approved text/CSV export or paste relevant content until an implementation
# has been selected, tested, and approved for the document's data classification.
#
# Proposed future usage: scripts/extract_document.sh inbox/documents/some-file.docx
# Proposed output: a .txt file beside the source; neither behavior is implemented.
#
# Possible implementation choices (not installed or verified by this kit):
#   .docx, .doc, .rtf  -> `textutil` (built into macOS, no install needed)
#   .pdf               -> `pdftotext` (brew install poppler if missing)
#   .pptx              -> textutil handles some; otherwise ask Claude to use
#                         python-docx/python-pptx (pip install --user python-pptx)
#   .xlsx              -> prefer re-exporting as .csv from Excel/Numbers directly;
#                         if that's not possible, python's openpyxl works too
#
set -e
FILE="$1"
if [ -z "$FILE" ]; then
  echo "Usage: $0 <path-to-file>"
  exit 1
fi

echo "No file was processed: extract_document.sh is a stub."
echo "Use an approved text/CSV export or paste relevant content until this format is implemented and tested."
exit 1
