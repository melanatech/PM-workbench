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
echo "27) Monthly review (dropped balls, decision quality)"
echo "28) To-do list (add, list, done, propose, sweep...)"
echo ""
read -p "Pick a number: " choice
read -p "Extra details (optional, press Enter to skip): " args

case $choice in
  1) cmd="/quick-close $args";;        2) cmd="/capture meeting-closeout $args";;
  3) cmd="/brief meeting-prep $args";;       4) cmd="/brief daily-brief";;
  5) cmd="/capture process-inbox";;            6) cmd="/sync jira-reconcile";;
  7) cmd="/discover discovery $args";;          8) cmd="/report okr-refresh";;
  9) cmd="/report weekly-update";;           10) cmd="/discover research-plan $args";;
  11) cmd="/build prd-package $args";;      12) cmd="/build prototype-build $args";;
  13) cmd="/build prd-prototype-sync $args";; 14) cmd="/discover research-package $args";;
  15) cmd="/build experiment-package $args";; 16) cmd="/build experiment-analyze $args";;
  17) cmd="/build launch-package $args";;   18) cmd="/sync roadmap-update $args";;
  19) cmd="/sync ripple-check $args";;     20) cmd="/discover competitive-scan $args";;
  21) cmd="/report strategy-refresh";;       22) cmd="/discover learn-product-flow $args";;
  23) cmd="/discover code-dive $args";;        24) cmd="/sync rotate-registers";;
  25) cmd="/brief return-brief $args";;
  26) cmd="/report workbench-health";;
  27) cmd="/report monthly-review $args";;
  28) cmd="/todo $args";;
  *) echo "Not a valid choice."; exit 1;;
esac

echo ""
echo "Running: $cmd"
echo "(Claude may ask permission for certain actions — that's the safety gate.)"
echo ""
claude "$cmd"
open outputs/ 2>/dev/null
