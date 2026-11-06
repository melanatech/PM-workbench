#!/usr/bin/env python3
"""PreToolUse twin of .claude/hooks/check_voice.py."""
from __future__ import annotations

import os
import runpy
import sys

TARGET = os.path.join(os.path.dirname(__file__), "..", "..", ".claude", "hooks", "check_voice.py")
sys.path.insert(0, os.path.dirname(__file__))
runpy.run_path(os.path.abspath(TARGET), run_name="__main__")
