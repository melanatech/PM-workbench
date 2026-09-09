#!/bin/bash
# Copy anything (Slack desktop, Outlook, a doc), double-click this, pick a category.
# It lands as a timestamped file in the right inbox folder, with source metadata.
cd "$(dirname "$0")"
CONTENT="$(pbpaste)"
if [ -z "$CONTENT" ]; then echo "Clipboard is empty — copy something first."; read -p "Press Enter to close."; exit 1; fi
echo "Save clipboard as:"
echo " 1) Discovery signal   2) Meeting notes   3) Research notes"
echo " 4) Competitive info   5) Launch material 6) Metric context"
read -p "Category: " cat
case $cat in
  1) dir="inbox/discovery";;  2) dir="inbox/meetings";;
  3) dir="inbox/research";;   4) dir="inbox/competitive";;
  5) dir="inbox/launches";;   6) dir="inbox/metrics";;
  *) echo "Invalid."; exit 1;;
esac
read -p "Short title (optional): " title
read -p "Source URL (optional): " url
ts=$(date +%Y-%m-%d-%H%M%S)
file="$dir/capture-$ts.md"
{
  echo "---"
  echo "captured_at: $(date -Iseconds)"
  echo "title: \"$title\""
  echo "source_url: \"$url\""
  echo "---"
  echo ""
  echo "$CONTENT"
} > "$file"
echo "Saved: $file  (processed on next /process-inbox run)"
read -p "Press Enter to close."
