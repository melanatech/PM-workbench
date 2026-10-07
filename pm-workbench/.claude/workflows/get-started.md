---
description: "How do I get started — create a live workspace and the first-week path for non-technical PMs"
model: haiku
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Audience:** someone who opened this project in Claude Code / Cursor and is not going to read all the markdown first. Prefer doing the bootstrap over explaining it. Keep jargon minimal.

**Not for:** scheduled / unattended runs. If this run has nobody to ask (rule 22), append `BLOCKED: get-started needs an interactive user` to `logs/run-log.csv` (create `logs/` if needed) and stop — never create a live folder unattended.

**Org-specific packs stay out of this workflow.** If the PM mentions a company seed zip / playbook their team shared, tell them to unpack it **after** the live folder exists (`reference/context/` + `reference/templates/`). Do not invent company URLs or templates here.

---

## Step 0 — Where am I?

Inspect the **current workspace root** (first open folder):

| Signal | Meaning |
|---|---|
| `scripts/create_live_workspace.py` exists **and** `START HERE.md` / `NEW-USER-SETUP.md` exist | Likely the **kit clone** (or a kit copy). Bootstrap lives here. |
| `registers/` + `inbox/` exist, and there is **no** `create_live_workspace.py` at this root (or `.claude` is a symlink into a kit) | Likely already a **live** workspace. |
| `~/.pm-workbench/live-root` points at this folder | Confirmed live marker from a prior bootstrap. |

Also check whether `~/pm-live` (or another path the PM already named) already exists and is non-empty.

---

## Path A — Already in a live workspace

Say so in one sentence. Do **not** re-run `create_live_workspace.py`.

Then give a short first-week card (chat only; optional save to `outputs/daily/YYYY-MM-DD-get-started.md` if useful):

1. Fill `.claude/CLAUDE.local.md` (machine, editor, tools you actually have — never invent connectors).
2. Optional: fictional practice in a **separate** isolate — from the kit: `python3 scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly` (never load the fixture into the live folder).
3. Drop a real meeting note in `inbox/meetings/` → `/capture meeting-closeout` or `/quick-close`.
4. Chrome clips → `/capture process-inbox`.
5. Point at `NEW-USER-SETUP.md` only for browser / scheduling / stubs when they ask.

Stop. Do not run Phase 2 product seeding unless they have an org playbook and ask for it.

---

## Path B — In the kit (or no live yet) — bootstrap

### B1 — Ask once (batched)

If any answer is missing, ask in **one** message then wait:

1. Live folder path? Default `~/pm-live` if they shrug.
2. Will they **edit the kit** (contributor / `--dev-links`) or just **use** it (copy mode)? Default = copy / use.
3. Confirm destination is empty or does not exist. If non-empty, stop and ask for a different path — the script never overwrites.

### B2 — Create the live folder (Tier 1 local)

From the **kit** root (repo root that contains `pm-workbench/` **or** the inner `pm-workbench/` folder — use whichever path makes the script resolve):

```sh
# Normal PM (copy kit into live)
python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live
# If cwd is already the inner pm-workbench/:
#   python3 scripts/create_live_workspace.py ~/pm-live

# Contributor only (when they chose edit-kit):
python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live --dev-links
```

Prefer **running** the script yourself with the Shell tool over pasting it for them to copy. On failure, show the error and the matching row from `NEW-USER-SETUP.md` troubleshooting — do not invent a workaround that overwrites data.

After success, print the script’s “Next steps” to the PM in plain language.

### B3 — Mandatory handoff

Tell them clearly:

1. **File → Open Folder** on the new live path (e.g. `~/pm-live`) — make it the **first** (or only) folder. Slash commands and hooks run from live, not from living only in the git clone.
2. In the new folder, they can say “how do I get started” again (Path A) or start with `/quick-close` / `/capture`.
3. Optional org seed pack: unpack after open, if their team gave them one.
4. Full checklist remains in `NEW-USER-SETUP.md` / `START HERE.md` in the kit — they do not need to read it upfront.

Do **not** end on “ready when you are” without stating the Open Folder step.

---

## Path C — Ambiguous / blocked

If you cannot tell kit vs live, or Python is missing: say what you checked, what failed, and the one thing they should do (install Python 3, open the kit clone, or name a destination). Offer the fallback: they run the `create_live_workspace.py` line from `START HERE.md` in Terminal and come back.

---

## RESULT shape

- Which path (A / B / C)
- Live path created or confirmed
- Exact next human action (usually: open live folder)
- What you ran (command + exit), if anything

No company-specific links. No Playwright / Artifactory rabbit holes on day one.
