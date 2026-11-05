#!/usr/bin/env bash
# Weekday LaunchAgents for the three unattended tasks. Weekly and monthly stay manual.
# daily-brief and todo-sweep get 7, 9 and 11 o'clock slots and run once per day (the first that succeeds).
# launchd runs a missed calendar job once at wake; cron skips it.
# --with-measurement also installs the two no-model script jobs (Fridays: metrics-snapshot 16:00,
# workbench-health 16:15). Opt in only after the three above have run cleanly for a week.
#
#   bash scripts/install_schedules.sh
#   bash scripts/install_schedules.sh --root ~/pm-live
#   bash scripts/install_schedules.sh --with-measurement
#   bash scripts/install_schedules.sh --dry-run [--with-measurement]   # print the plists; write and load nothing
#   bash scripts/install_schedules.sh --uninstall
#
# PATH is the launchd-like environment that completed daily-brief:
#   env -i HOME=$HOME PATH=/usr/bin:/bin:$HOME/.gocode/shims \
#     python3 scripts/run_scheduled.py daily-brief

set -euo pipefail

ROOT=""
UNINSTALL=0
DRY_RUN=0
MEASUREMENT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --with-measurement) MEASUREMENT=1; shift ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -z "$ROOT" ]]; then
  if [[ -n "${PM_LIVE_ROOT:-}" ]]; then
    ROOT="$PM_LIVE_ROOT"
  elif [[ -f "$HOME/.pm-workbench/live-root" ]]; then
    ROOT="$(grep -v '^#' "$HOME/.pm-workbench/live-root" | head -1 | tr -d '[:space:]')"
  else
    ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  fi
fi
ROOT="$(cd "$ROOT" && pwd)"

PYTHON="/usr/bin/python3"
RUNNER="$ROOT/scripts/run_scheduled.py"
LOG_DIR="$ROOT/logs"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
# Verified 2026-10-19: this PATH plus HOME is enough for headless `claude` (GoCode shim).
PATH_VALUE="/usr/bin:/bin:${HOME}/.gocode/shims"
LABELS=(
  com.pm-workbench.daily-brief
  com.pm-workbench.todo-sweep
  com.pm-workbench.inbox-watch
  com.pm-workbench.metrics-snapshot
  com.pm-workbench.workbench-health
)

if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p "$LOG_DIR" "$AGENTS" "$HOME/.pm-workbench"
  printf '%s\n' "$ROOT" > "$HOME/.pm-workbench/live-root"
fi

bootout_one() {
  local label="$1"
  local plist="$AGENTS/${label}.plist"
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || launchctl unload "$plist" 2>/dev/null || true
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  for label in "${LABELS[@]}"; do
    bootout_one "$label"
    rm -f "$AGENTS/${label}.plist"
    echo "uninstalled $label"
  done
  exit 0
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "missing $PYTHON" >&2
  exit 1
fi
if [[ ! -f "$RUNNER" ]]; then
  echo "missing $RUNNER — run from a live workspace that has scripts/" >&2
  exit 1
fi
if [[ ! -d "$HOME/.gocode/shims" ]]; then
  echo "WARNING: $HOME/.gocode/shims is not there, so launchd may not find claude." >&2
fi

# Weekday is 1–5 (Monday–Friday). 0 and 7 are Sunday.
calendar_block() {
  local minute="$1"
  shift
  local day hour
  echo "  <key>StartCalendarInterval</key>"
  echo "  <array>"
  for day in 1 2 3 4 5; do
    for hour in "$@"; do
      cat <<EOF
    <dict>
      <key>Hour</key>
      <integer>${hour}</integer>
      <key>Minute</key>
      <integer>${minute}</integer>
      <key>Weekday</key>
      <integer>${day}</integer>
    </dict>
EOF
    done
  done
  echo "  </array>"
}

# One weekday: calendar_weekly <weekday 1-5> <hour> <minute>
calendar_weekly() {
  cat <<EOF
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$2</integer>
    <key>Minute</key>
    <integer>$3</integer>
    <key>Weekday</key>
    <integer>$1</integer>
  </dict>
EOF
}

install_one() {
  local task="$1"
  local calendar="$2"
  shift 2
  local label="com.pm-workbench.${task}"
  local plist="$AGENTS/${label}.plist"
  local args_xml=""
  local arg
  for arg in "$@"; do
    args_xml+="    <string>${arg}</string>"$'\n'
  done

  local content
  content="$(cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${RUNNER}</string>
${args_xml}  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>${HOME}</string>
    <key>PATH</key>
    <string>${PATH_VALUE}</string>
  </dict>
${calendar}
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/sched-${task}.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/sched-${task}.err.log</string>
</dict>
</plist>
EOF
)"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "# $plist"
    printf '%s\n' "$content"
    return 0
  fi
  printf '%s\n' "$content" > "$plist"
  chmod 644 "$plist"
  plutil -lint "$plist" >/dev/null
  bootout_one "$label"
  launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null || launchctl load "$plist"
  echo "installed $label"
}

# 9:xx and 11:xx are catch-up slots: --once-per-day skips them after a run logged ok that day.
CAL_BRIEF="$(calendar_block 27 7 9 11)"
CAL_SWEEP="$(calendar_block 43 7 9 11)"
CAL_INBOX="$(calendar_block 12 8 9 10 11 12 13 14 15 16 17 18)"

install_one daily-brief "$CAL_BRIEF" daily-brief --once-per-day
install_one todo-sweep "$CAL_SWEEP" todo-sweep --once-per-day
install_one inbox-watch "$CAL_INBOX" inbox-watch --if-new-inbox
if [[ "$MEASUREMENT" -eq 1 ]]; then
  install_one metrics-snapshot "$(calendar_weekly 5 16 0)" metrics-snapshot
  install_one workbench-health "$(calendar_weekly 5 16 15)" workbench-health
fi
[[ "$DRY_RUN" -eq 1 ]] && exit 0

echo "working directory: $ROOT"
echo "logs: $LOG_DIR/sched-<task>.{out,err}.log"
echo "uninstall: bash scripts/install_schedules.sh --uninstall"
