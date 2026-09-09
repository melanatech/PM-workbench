#!/bin/bash
# PM Workbench menu — double-click to run. No terminal knowledge needed.
cd "$(dirname "$0")"
echo "==============================="
echo "        PM WORKBENCH"
echo "==============================="
echo " 1) Process new inbox items"
echo " 2) Close out a meeting"
echo " 3) Reconcile Jira board"
echo " 4) Discovery scan (weekly)"
echo " 5) Refresh OKRs"
echo " 6) Draft weekly leadership update"
echo " 7) Find research candidates"
echo " 8) Create PRD package"
echo " 9) Build a prototype"
echo "10) Create research/test package"
echo "11) Create experiment package"
echo "12) Analyze experiment results"
echo "13) Create launch package"
echo "14) Competitive scan"
echo "15) Refresh product strategy"
echo "16) Learn a product flow"
echo "17) Code dive on a feature"
echo "18) Return-to-work brief (one-time)"
echo ""
read -p "Pick a number: " choice
read -p "Extra details (optional, press Enter to skip): " args

case $choice in
  1) cmd="/process-inbox";;      2) cmd="/meeting-closeout $args";;
  3) cmd="/jira-reconcile";;     4) cmd="/discovery-delta";;
  5) cmd="/okr-refresh";;        6) cmd="/weekly-update";;
  7) cmd="/find-users $args";;   8) cmd="/prd-package $args";;
  9) cmd="/prototype-build $args";; 10) cmd="/research-package $args";;
  11) cmd="/experiment-package $args";; 12) cmd="/experiment-analyze $args";;
  13) cmd="/launch-package $args";; 14) cmd="/competitive-scan $args";;
  15) cmd="/strategy-refresh";;  16) cmd="/learn-product-flow $args";;
  17) cmd="/code-dive $args";;   18) cmd="/return-brief $args";;
  *) echo "Not a valid choice."; exit 1;;
esac

echo ""
echo "Running: $cmd"
echo "(Claude may ask permission for certain actions — that's the safety gate.)"
echo ""
claude "$cmd"
open outputs/ 2>/dev/null
