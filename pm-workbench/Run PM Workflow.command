#!/bin/bash
# PM Workbench menu — double-click to run. No terminal knowledge needed.
cd "$(dirname "$0")"
echo "==============================="
echo "        PM WORKBENCH"
echo "==============================="
echo " 1) Quick close (60-second capture)"
echo " 2) Close out a meeting"
echo " 3) Prep for a meeting"
echo " 4) Daily brief"
echo " 5) Process new inbox items"
echo " 6) Reconcile Jira board"
echo " 7) Discovery (ask / add / what's new / map)"
echo " 8) Refresh OKRs"
echo " 9) Draft weekly leadership update"
echo "10) Research plan (criteria, outreach, guide)"
echo "11) Create PRD package"
echo "12) Build a prototype"
echo "13) PRD <-> prototype sync check"
echo "14) Create research/test package"
echo "15) Create experiment package"
echo "16) Analyze experiment results"
echo "17) Create launch package"
echo "18) Roadmap update"
echo "19) Ripple check (what else does this affect)"
echo "20) Competitive scan"
echo "21) Refresh product strategy"
echo "22) Learn a product flow"
echo "23) Code dive on a feature"
echo "24) Rotate registers"
echo "25) Return-to-work brief (one-time)"
echo "26) Workbench health (what do I actually use)"
echo ""
read -p "Pick a number: " choice
read -p "Extra details (optional, press Enter to skip): " args

case $choice in
  1) cmd="/quick-close $args";;        2) cmd="/meeting-closeout $args";;
  3) cmd="/meeting-prep $args";;       4) cmd="/daily-brief";;
  5) cmd="/process-inbox";;            6) cmd="/jira-reconcile";;
  7) cmd="/discovery $args";;          8) cmd="/okr-refresh";;
  9) cmd="/weekly-update";;           10) cmd="/research-plan $args";;
  11) cmd="/prd-package $args";;      12) cmd="/prototype-build $args";;
  13) cmd="/prd-prototype-sync $args";; 14) cmd="/research-package $args";;
  15) cmd="/experiment-package $args";; 16) cmd="/experiment-analyze $args";;
  17) cmd="/launch-package $args";;   18) cmd="/roadmap-update $args";;
  19) cmd="/ripple-check $args";;     20) cmd="/competitive-scan $args";;
  21) cmd="/strategy-refresh";;       22) cmd="/learn-product-flow $args";;
  23) cmd="/code-dive $args";;        24) cmd="/rotate-registers";;
  25) cmd="/return-brief $args";;
  26) cmd="/workbench-health";;
  *) echo "Not a valid choice."; exit 1;;
esac

echo ""
echo "Running: $cmd"
echo "(Claude may ask permission for certain actions — that's the safety gate.)"
echo ""
claude "$cmd"
open outputs/ 2>/dev/null
