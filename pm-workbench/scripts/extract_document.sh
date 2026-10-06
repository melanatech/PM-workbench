#!/usr/bin/env bash
# Extract plain text from a document into a sibling .txt file.
#
# Usage: scripts/extract_document.sh <path>
# Output: <path-without-ext>.extracted.txt (printed as the last line on success)
#
# Supported (best-effort, macOS-first):
#   .txt .md .csv .tsv     — copy through
#   .doc .docx .rtf .rtfd .html .htm .odt — textutil
#   .pdf                  — pdftotext if installed, else PDFKit via swift
#
# Charts / image-only slides are NOT in the text output. For those, also run:
#   scripts/rasterize_pdf.sh <path.pdf>   → <stem>.pages/page-NN.png
# process-inbox and internal-docs-reader Read those PNGs with vision.
#
# Exit codes:
#   0 success (path printed)
#   1 usage / missing file
#   2 unsupported or empty extraction — use re-export/paste (message on stderr)
#   3 tool failure (encrypted sensitivity label, corrupt file, etc.)
#
# Do not invent alternate extractors when this returns 0. On 2/3, prefer
# re-export/paste over spinning up new one-off scripts unless the PM asks.
#
set -euo pipefail

FILE="${1:-}"
if [[ -z "$FILE" ]]; then
  echo "Usage: $0 <path-to-file>" >&2
  exit 1
fi
if [[ ! -f "$FILE" ]]; then
  echo "Not a file: $FILE" >&2
  exit 1
fi

abs="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
base="${abs%.*}"
# Avoid clobbering an existing .txt sibling that might be the source itself
out="${base}.extracted.txt"
ext="$(printf '%s' "${abs##*.}" | tr '[:upper:]' '[:lower:]')"

copy_through() {
  cp "$abs" "$out"
  echo "$out"
  exit 0
}

extract_textutil() {
  if ! command -v textutil >/dev/null 2>&1; then
    echo "textutil not found (macOS only for this path)." >&2
    return 3
  fi
  # textutil writes the output path we give it
  if ! textutil -convert txt "$abs" -output "$out" 2>/tmp/pmwb-extract-err.$$; then
    echo "textutil failed for $abs:" >&2
    cat /tmp/pmwb-extract-err.$$ >&2 || true
    rm -f /tmp/pmwb-extract-err.$$
    return 3
  fi
  rm -f /tmp/pmwb-extract-err.$$
  if [[ ! -s "$out" ]]; then
    echo "textutil produced empty text (encrypted/sensitivity-labelled Office files often fail here). Re-export as .txt/.pdf without protection, or paste." >&2
    rm -f "$out"
    return 3
  fi
  echo "$out"
  return 0
}

extract_pdf() {
  if command -v pdftotext >/dev/null 2>&1; then
    if pdftotext -layout "$abs" "$out" 2>/tmp/pmwb-extract-err.$$; then
      rm -f /tmp/pmwb-extract-err.$$
      if [[ -s "$out" ]]; then
        echo "$out"
        return 0
      fi
    fi
    rm -f /tmp/pmwb-extract-err.$$
  fi
  if ! command -v swift >/dev/null 2>&1; then
    echo "No pdftotext (brew install poppler) and no swift/PDFKit. Re-export PDF text or paste." >&2
    return 2
  fi
  # PDFKit — same approach previously used as a one-off; now kit-owned
  if ! EXTRACT_SRC="$abs" EXTRACT_DST="$out" swift -e '
import Foundation
import PDFKit
let src = ProcessInfo.processInfo.environment["EXTRACT_SRC"]!
let dst = ProcessInfo.processInfo.environment["EXTRACT_DST"]!
guard let doc = PDFDocument(url: URL(fileURLWithPath: src)) else {
  fputs("PDFKit could not open file (encrypted or corrupt?). Re-export or paste.\n", stderr)
  exit(3)
}
var text = ""
for i in 0..<doc.pageCount {
  if let page = doc.page(at: i), let s = page.string {
    text += s
    text += "\n"
  }
}
guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
  fputs("PDFKit extracted no text (scan/image-only PDF?). Use OCR export or paste.\n", stderr)
  exit(3)
}
try text.write(to: URL(fileURLWithPath: dst), atomically: true, encoding: .utf8)
' 2>/tmp/pmwb-extract-err.$$; then
    echo "PDF extract failed for $abs:" >&2
    cat /tmp/pmwb-extract-err.$$ >&2 || true
    rm -f /tmp/pmwb-extract-err.$$ "$out"
    return 3
  fi
  rm -f /tmp/pmwb-extract-err.$$
  echo "$out"
  return 0
}

case "$ext" in
  txt|md|csv|tsv|json|log)
    copy_through
    ;;
  doc|docx|rtf|rtfd|html|htm|odt|webarchive)
    extract_textutil
    exit $?
    ;;
  pdf)
    extract_pdf
    exit $?
    ;;
  ppt|pptx|xls|xlsx|key|pages|numbers)
    echo "Unsupported in-kit extract for .$ext. Re-export as .txt/.csv/.pdf (or paste), then re-run process-inbox." >&2
    exit 2
    ;;
  *)
    echo "Unknown extension .$ext. Try re-export as .txt/.pdf or paste." >&2
    exit 2
    ;;
esac
