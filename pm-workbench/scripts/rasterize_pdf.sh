#!/usr/bin/env bash
# Render PDF pages to PNGs so Claude can Read them with vision.
#
# Usage: scripts/rasterize_pdf.sh <path-to.pdf> [max_pages]
# Output dir: <path-without-ext>.pages/  (page-01.png …)
# Prints the directory path on success (last line).
#
# macOS: PDFKit via swift (no Homebrew). Optional: pdftoppm if poppler is installed.
# Default max_pages=40 (disk safety). Vision workflows may read fewer.
#
# Exit: 0 ok | 1 usage/missing | 2 not a pdf | 3 render failure
#
set -euo pipefail

FILE="${1:-}"
MAX_PAGES="${2:-${PMWB_PDF_MAX_PAGES:-40}}"

if [[ -z "$FILE" ]]; then
  echo "Usage: $0 <path-to.pdf> [max_pages]" >&2
  exit 1
fi
if [[ ! -f "$FILE" ]]; then
  echo "Not a file: $FILE" >&2
  exit 1
fi

abs="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
ext="$(printf '%s' "${abs##*.}" | tr '[:upper:]' '[:lower:]')"
if [[ "$ext" != "pdf" ]]; then
  echo "Not a PDF: $abs" >&2
  exit 2
fi

base="${abs%.*}"
outdir="${base}.pages"
mkdir -p "$outdir"
# Clear prior rasters for this stem so page counts stay honest
rm -f "$outdir"/page-*.png "$outdir"/manifest.txt

if command -v pdftoppm >/dev/null 2>&1; then
  if pdftoppm -png -r 150 -f 1 -l "$MAX_PAGES" "$abs" "$outdir/page"; then
    # pdftoppm names page-1.png; normalize to page-01.png
    shopt -s nullglob
    for f in "$outdir"/page-*.png; do
      bn="$(basename "$f")"
      num="${bn#page-}"
      num="${num%.png}"
      if [[ "$num" =~ ^[0-9]+$ ]]; then
        printf -v padded '%02d' "$((10#$num))"
        mv -f "$f" "$outdir/page-${padded}.png"
      fi
    done
    shopt -u nullglob
  fi
fi

count="$(find "$outdir" -maxdepth 1 -name 'page-*.png' | wc -l | tr -d ' ')"
if [[ "$count" -eq 0 ]]; then
  if ! command -v swift >/dev/null 2>&1; then
    echo "Need pdftoppm (brew install poppler) or swift/PDFKit to rasterize." >&2
    exit 3
  fi
  if ! EXTRACT_SRC="$abs" EXTRACT_DST="$outdir" MAX_PAGES="$MAX_PAGES" swift -e '
import Foundation
import PDFKit
import AppKit
let src = ProcessInfo.processInfo.environment["EXTRACT_SRC"]!
let dst = ProcessInfo.processInfo.environment["EXTRACT_DST"]!
let maxPages = Int(ProcessInfo.processInfo.environment["MAX_PAGES"] ?? "40") ?? 40
guard let doc = PDFDocument(url: URL(fileURLWithPath: src)) else {
  fputs("PDFKit could not open PDF.\n", stderr)
  exit(3)
}
let n = min(doc.pageCount, maxPages)
let size = CGSize(width: 1600, height: 1600)
var written = 0
for i in 0..<n {
  guard let page = doc.page(at: i) else { continue }
  let img = page.thumbnail(of: size, for: .mediaBox)
  guard let tiff = img.tiffRepresentation,
        let rep = NSBitmapImageRep(data: tiff),
        let png = rep.representation(using: .png, properties: [:]) else {
    fputs("Failed to render page \(i+1)\n", stderr)
    continue
  }
  let name = String(format: "page-%02d.png", i + 1)
  let path = (dst as NSString).appendingPathComponent(name)
  do {
    try png.write(to: URL(fileURLWithPath: path))
    written += 1
  } catch {
    fputs("Write failed \(name): \(error)\n", stderr)
  }
}
if written == 0 {
  fputs("No pages rendered.\n", stderr)
  exit(3)
}
var manifest = "source=\(src)\ntotal_pdf_pages=\(doc.pageCount)\nrasterized=\(written)\nmax_pages=\(maxPages)\n"
FileManager.default.createFile(atPath: (dst as NSString).appendingPathComponent("manifest.txt"), contents: manifest.data(using: .utf8), attributes: nil)
' 2>/tmp/pmwb-rasterize-err.$$; then
    echo "PDF rasterize failed for $abs:" >&2
    cat /tmp/pmwb-rasterize-err.$$ >&2 || true
    rm -f /tmp/pmwb-rasterize-err.$$
    exit 3
  fi
  rm -f /tmp/pmwb-rasterize-err.$$
else
  # pdftoppm path — write a simple manifest
  {
    echo "source=$abs"
    echo "rasterized=$count"
    echo "max_pages=$MAX_PAGES"
  } > "$outdir/manifest.txt"
fi

echo "$outdir"
exit 0
