"""Shared helpers for the workbench hooks. Every hook fails OPEN: an internal error
prints a one-line warning and exits 0, so a broken hook can never block your work."""
import sys, json, os

def payload():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}

def root():
    return os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()

def rel(path):
    try:
        return os.path.relpath(path, root()).replace(os.sep, '/')
    except Exception:
        return path

def block(msg):
    """Exit 2 = Claude Code blocks the tool call and shows Claude the message."""
    sys.stderr.write(msg.strip() + "\n")
    sys.exit(2)

def warn(msg):
    sys.stderr.write("[workbench hook] " + msg.strip() + "\n")
    sys.exit(0)
