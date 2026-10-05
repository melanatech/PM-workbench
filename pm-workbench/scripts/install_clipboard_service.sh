#!/usr/bin/env bash
# Install right-click Services capture for desktop apps (Slack, Mail, Notes…).
# Builds a real Cocoa NSServices app with Swift (shell/Automator stubs cannot
# receive selected text). Writes into the live workspace via live-root.

set -euo pipefail

ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/install_clipboard_service.sh [--root ~/pm-live]"
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Right-click Services is macOS-only (Windows has no equivalent for selected text)."
  echo "On this OS: copy text, then run:"
  echo "  python3 scripts/capture_clipboard.py --gui"
  echo "Chrome: use the Workbench Clipper (works on Windows too)."
  exit 0
fi

if [[ -z "$ROOT" && -n "${PM_LIVE_ROOT:-}" ]]; then ROOT="$PM_LIVE_ROOT"; fi
if [[ -z "$ROOT" && -f "$HOME/.pm-workbench/live-root" ]]; then
  ROOT="$(grep -v '^#' "$HOME/.pm-workbench/live-root" | head -1 | tr -d '[:space:]' || true)"
fi
if [[ -z "$ROOT" ]]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
ROOT="$(cd "$ROOT" && pwd)"

CAPTURE_PY="$ROOT/scripts/capture_clipboard.py"
if [[ ! -f "$CAPTURE_PY" ]]; then
  CAPTURE_PY="$(cd "$(dirname "$0")" && pwd)/capture_clipboard.py"
fi
if [[ ! -f "$CAPTURE_PY" ]]; then
  echo "Missing capture_clipboard.py" >&2
  exit 1
fi

KIT_TOOLS="$(cd "$(dirname "$0")/.." && pwd)/tools/clipboard-capture"
SRC="$KIT_TOOLS/SendToPMWorkbench/main.swift"
if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC" >&2
  exit 1
fi

# live-root marker (best-effort; sandbox may block)
mkdir -p "$HOME/.pm-workbench" 2>/dev/null || true
{ printf '%s\n' "$ROOT" > "$HOME/.pm-workbench/live-root"; } 2>/dev/null || true

# Remove broken Automator / Spotlight stubs from earlier attempts
rm -rf "$HOME/Library/Services/Send to PM Workbench.workflow" 2>/dev/null || true

APP_DIR="$HOME/Applications/Send to PM Workbench.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

# Build binary into a workspace-writable staging dir first (sandbox-safe compile),
# then copy into ~/Applications (needs a normal Terminal session).
STAGE="$KIT_TOOLS/SendToPMWorkbench/build"
mkdir -p "$STAGE" "$MACOS" "$RESOURCES"

BIN="$STAGE/Send to PM Workbench"
if command -v swiftc >/dev/null 2>&1; then
  echo "Compiling Services app…"
  ARCH="$(uname -m)"
  swiftc -O -parse-as-library \
    -framework AppKit -framework Foundation \
    -target "${ARCH}-apple-macos13.0" \
    -o "$BIN" \
    "$SRC"
elif [[ -x "$BIN" ]]; then
  echo "swiftc missing — using prebuilt binary at $BIN"
else
  echo "swiftc not found. Install Command Line Tools: xcode-select --install" >&2
  exit 1
fi

if ! cp "$BIN" "$MACOS/Send to PM Workbench" 2>/dev/null; then
  echo "" >&2
  echo "Could not write $APP_DIR" >&2
  echo "Run this same command in Terminal.app (outside Cursor sandbox):" >&2
  echo "  cd ~/pm-live && bash scripts/install_clipboard_service.sh" >&2
  exit 1
fi
chmod +x "$MACOS/Send to PM Workbench"
cp "$CAPTURE_PY" "$RESOURCES/capture_clipboard.py"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>Send to PM Workbench</string>
  <key>CFBundleIdentifier</key>
  <string>com.pm-workbench.send-to-pmwb</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Send to PM Workbench</string>
  <key>CFBundleDisplayName</key>
  <string>Send to PM Workbench</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>2.0</string>
  <key>CFBundleVersion</key>
  <string>2.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>LSUIElement</key>
  <true/>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSServices</key>
  <array>
    <dict>
      <key>NSMenuItem</key>
      <dict>
        <key>default</key>
        <string>Send to PM Workbench</string>
      </dict>
      <key>NSMessage</key>
      <string>processText</string>
      <key>NSPortName</key>
      <string>Send to PM Workbench</string>
      <key>NSSendTypes</key>
      <array>
        <string>NSStringPboardType</string>
        <string>public.utf8-plain-text</string>
        <string>public.text</string>
      </array>
      <key>NSRequiredContext</key>
      <dict/>
    </dict>
  </array>
</dict>
</plist>
PLIST

/usr/bin/touch "$APP_DIR"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"$LSREGISTER" -f "$APP_DIR" 2>/dev/null || true
/System/Library/CoreServices/pbs -flush 2>/dev/null || true

echo ""
echo "Installed: $APP_DIR"
echo "live-root → $ROOT"
echo ""
echo "Enable once:"
echo "  System Settings → Keyboard → Keyboard Shortcuts → Services"
echo "  → Text → turn ON “Send to PM Workbench”"
echo "  (Not under Privacy & Security.)"
echo ""
echo "Use:"
echo "  Select text → right-click → Services → Send to PM Workbench"
echo "  If an app (e.g. some Slack builds) hides Services on right-click:"
echo "  menu bar → Slack → Services → Send to PM Workbench"
echo ""
echo "Optional: assign a shortcut in that same Keyboard Shortcuts → Services list."
