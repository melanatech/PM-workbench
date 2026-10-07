---
name: get-started
description: >
  Use when the PM says how do I get started, set up the workbench, create my pm-live,
  first-time setup, new user setup, or onboarding to this kit. Runs /brief get-started.
  Never improvise a partial README paraphrase that skips create_live_workspace.py.
---

# get-started

Plain-language entry for **`/brief get-started`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/get-started.md` in full (same gates as the slash command). Prefer dispatching via the `/brief` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Prefer running `scripts/create_live_workspace.py` when Path B applies — do not only paste docs.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command; loading the lumenly fixture into `~/pm-live`; putting org-specific templates into the public kit.
