# NEW-USER-SETUP — get a live workspace running in Claude Code

This kit is not an app you start. It is Claude Code commands, hooks, and local
Python scripts. Real work happens in a **non-git live folder**; the git clone
stays the source of kit fixes.

## 0. Preflight (2 minutes)

```sh
python3 --version          # 3.x required; no pip packages for core scripts
which claude && claude --version
claude auth status         # must show logged in for slash commands / scheduling
```

Optional for browser paths later:

```sh
node --version && npx --version
ls "/Applications/Google Chrome.app" 2>/dev/null || echo "Chrome optional for now"
```

### Keep Claude Code current

The **Cursor Claude Code extension** and the **`claude` CLI** can drift apart.
On first setup, the CLI was older than the extension (e.g. CLI `2.1.119` while
Cursor had `2.1.288`). Before relying on scheduling or `claude -p`, update the
CLI and re-check:

```sh
claude update
# or: npm i -g @anthropic-ai/claude-code@latest
claude --version
```

You do not need a brand-new CLI to try slash commands in the Cursor extension
panel, but keep them aligned so unattended runs see the same flags and behavior.

### Cursor Agent vs Claude Code extension vs terminal CLI

| Surface | Use it for workbench? |
|---|---|
| **Claude Code extension in Cursor** (panel) | **Yes — primary.** Open `~/pm-live`, type `/capture` and the other commands here. |
| **Cursor Agent chat** (this product’s Agent) | **No.** It does not load `.claude/commands/`, hooks, or `workflow-runner`. |
| **Terminal `claude` / `claude -p`** | **Optional.** Useful later for `scripts/run_scheduled.py` and headless checks. Not required for the first capture. |

You do **not** need to use Cursor’s terminal as the main way to talk to Claude
Code. Prefer the extension panel with folder **`~/pm-live`** open (File → Open
Folder on that path, not the git repo root).

If a shell injects `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` for a company
proxy that cannot reach the API, `claude -p` will fail there even when the
Claude Code panel works after `/login`. That is an environment issue, not proof
the kit is broken — verify slash commands in the panel first.

**Amazon Bedrock and native WebSearch:** Bedrock does not implement Claude's
server-side `web_search` tool (errors like "Bedrock does not support the
web_search tool"). For `/discover competitive-scan`, the kit uses
`python3 scripts/web_search.py` (local DuckDuckGo search) instead — no
Bedrock support and no PM-supplied URL list required. Other workflows that
still call native WebSearch may need the same pattern if you see that error.

## 1. Clone once, then create a live workspace

```sh
git clone https://github.com/melanatech/PM-workbench.git
cd PM-workbench
```

**Normal users** (kit code is a snapshot; real data stays local):

```sh
python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live
```

**Contributors / first-run testers** (kit code symlinked so edits land in git):

```sh
python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live --dev-links
```

Preview without writing:

```sh
python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live --dry-run
```

Rules the script enforces:

- Destination must be empty (or not exist). Never overwrites.
- Destination must be outside `pm-workbench/`.
- Data dirs (`inbox/`, `registers/`, `state/`, `logs/`, `reference/`, …) are
  real directories, never symlinks (hooks refuse symlink register writes).
- `.git`, `.mcp.json`, `CLAUDE.local.md`, and source working data are not copied.

Open **`~/pm-live` as the first (or only) folder** in Cursor before starting a
Claude Code chat. The extension uses the **first workspace folder** as its
working directory; there is no supported `claudeCode.workingDirectory` setting
yet.

| Goal | How |
|---|---|
| Daily workbench use | File → Open Folder → `~/pm-live`. Keep the git clone in a **second window** if you need it. |
| Both folders in one window | In the Explorer, drag **pm-live above PM-workbench**. New Claude Code sessions follow the top folder. |
| macOS shortcut | `cursor "$HOME/pm-live"` from a terminal, or make a Dock/alias that runs that command. |
| Terminal CLI | `cd ~/pm-live && claude` (or `claude -p` from that directory). |

A chat that was started with the git clone first stays on that clone until you
open a **new** Claude Code session after the folder order is right. `/add-dir`
can grant extra access; it does not change the primary working directory.

## 2. Verify slash commands

In the Claude Code panel (with `~/pm-live` as the first folder), type `/` and confirm you see at least:

`capture`, `brief`, `sync`, `discover`, `build`, `report`, `quick-close`, `todo`

If they are missing, the project directory is wrong (git clone is first, or you
are in Cursor Agent) or Claude Code did not load `.claude/commands/`.

## 2b. Optional Claude Code plugins (user install — not in git)

These install into **your Claude Code user config**, not into the kit or
`~/pm-live`. Skip any your company has not approved. After install, authenticate
each plugin when prompted, then list what you actually use in
`.claude/CLAUDE.local.md` (and the approved brackets in `CLAUDE.md`). Workbench
rule 21 still applies: name the access path on every external read. Jira /
Confluence / Slack **writes** stay Tier 2–3 (show drafts; no silent send).

In the Claude Code panel:

```text
/plugin install atlassian@claude-plugins-official
/plugin install frontend-design@claude-plugins-official
/plugin install slack@claude-plugins-official
/plugin install github@claude-plugins-official
/plugin install figma@claude-plugins-official
/plugin install chrome-devtools-mcp@claude-plugins-official
```

| Plugin | Useful for |
|---|---|
| `atlassian` | Jira / Confluence reads for `/sync jira-reconcile` and wiki checks |
| `frontend-design` | Visual quality on `/build prototype-build` |
| `slack` | Channel/thread context when paste/export is not enough |
| `github` | Repo/PR lookups for prototypes and kit PRs (not a substitute for local `git`) |
| `figma` | Design tokens / frames when `reference/design/` is thin |
| `chrome-devtools-mcp` | Inspect a live Chrome tab (perf, network, DOM) — separate from the Workbench Clipper and Playwright `browser-bridge` |

If a plugin is “not found,” refresh the marketplace:
`/plugin marketplace update claude-plugins-official` (or
`/plugin marketplace add anthropics/claude-plugins-official`). Browse alternatives
with `/plugin` → Discover. Do **not** commit plugin auth tokens or
`installed_plugins.json` into this repo.

## 3. Isolated Lumenly fixture (fictional; separate folder)

From the **git clone**:

```sh
python3 -m unittest discover -s pm-workbench/tests -v
python3 pm-workbench/scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly
```

Open `/tmp/pm-workbench-lumenly` in Claude Code and run:

```text
/capture meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt
```

If the runner cannot dispatch, add `inline`. Then in that folder:

```sh
python3 scripts/check_run.py
python3 scripts/score_fixture.py
```

Compare with `pm-workbench/fixtures/lumenly/README.md`. Remove only the isolated
folder when finished. Do **not** load the fixture into `~/pm-live`.

## 4. First real local capture

In `~/pm-live`:

1. Put private context in `.claude/CLAUDE.local.md` (gitignored).
2. Seed `reference/links.csv` and `reference/context/current-priorities.md` with
   approved or public links only. Leave
   `reference/context/assumptions-and-open-questions.md` empty — capture fills it.
3. Drop a meeting transcript into `inbox/meetings/`.
4. Run `/capture meeting-closeout inbox/meetings/<your-file>.txt` (or
   `/capture process-inbox` for a batch). That run should: write DEC-/COM-/RISK-
   rows; **seed** `registers/initiatives.csv` for named product work; append
   assumptions/open questions; update `learning/[area].md` when the meeting
   taught product behavior; queue your personal follow-ups under
   `outputs/todo-proposals/` (nothing is added to `registers/todos.csv` until
   you run `/todo propose` and accept).
5. Run `python3 scripts/check_run.py`.
6. Run `/todo propose` and accept the ones you want on your list.

Also try `/quick-close`, `/todo`, `/brief daily-brief`, and
`/report workbench-health` once.

## 5. Troubleshooting map

| Symptom | Likely cause | What to do |
|---|---|---|
| `/capture` missing | Project is the git root, or you are in Cursor Agent not Claude Code | Open `~/pm-live` in the Claude Code extension panel |
| CLI much older than Cursor extension | Separate install channels | `claude update` (or npm global update); compare `claude --version` to the extension |
| `claude -p` ConnectionRefused / timeout | Shell proxy `ANTHROPIC_BASE_URL` unreachable | Use Claude Code panel; or `/login` in a clean shell without that proxy |
| `claude -p` “Not logged in” | No standalone OAuth in that shell | Run `/login` in Claude Code / the CLI |
| Clip lands in Downloads, Claude does not see it | Chrome cannot write outside Downloads; pull not run yet | In Claude Code: `/capture process-inbox` (step 0 runs `pull_clips.py`) or ask it to run `python3 scripts/pull_clips.py`. Approve the Bash prompt. No Full Disk Access needed for that path |
| Constant Bash / `python3` approval prompts | **Edit automatically** does not auto-run scripts; your mode menu may lack **Auto** | Start a **new** Claude Code chat (user `~/.claude/settings.json` already allows `Bash(python3 *)`). Type `/permissions` to add more. Or extension setting **Allow dangerously skip permissions** → Bypass if it appears |
| Clip cuts off mid-meeting | Old extension, or **Selection only** used | `chrome://extensions` → **Reload** clipper; use **Meeting notes / summary** (scrapes transcript DOM). Avoid Selection only for Stream |
| Menu has no "full page" / still 6 flat items | Extension not reloaded after kit update | Reload PM Workbench Clipper on `chrome://extensions` (v0.3+); primary items now always scrape the page/transcript |
| Output path in chat is not clickable | Link used `file://` or absolute `/Users/...`, or wrong folder is first | Claude Code only clicks **workspace-relative** paths under the **first** folder. Open `~/pm-live` first (or alone). Expect `[outputs/daily/….md](outputs/daily/….md)` |
| Hooks seem skipped | Fail-open by design, or settings not loaded | Check `logs/run-log.csv`; run `python3 scripts/check_run.py` |
| `npm install -g @playwright/mcp` → EACCES | No write to global node_modules | Use `npx --yes @playwright/mcp@latest` in `.mcp.json` (no global install) |
| Chrome debug port dead | Profile/flags | Retry with a dedicated `$HOME/chrome-claude-profile`; headless CDP works for smoke tests |
| Stub scripts exit with a message | Expected | Use markdown/CSV/paste fallbacks until you implement a real branch |
| `create_live_workspace.py` refuses destination | Non-empty or inside kit | Pick a new empty path outside `pm-workbench/` |

## 6. Where real data lives

| Path | Commit to git? |
|---|---|
| Git clone `pm-workbench/` kit files | Yes (logic only) |
| `~/pm-live/inbox`, `registers`, `outputs`, `state`, `logs` | No |
| `~/pm-live/reference/links.csv` with internal URLs | No |
| `.claude/CLAUDE.local.md` | No (gitignored) |
| `~/pm-live/.mcp.json` | No (local only) |

**Copy mode vs `--dev-links`:** copy mode snapshots kit code; update by creating a
new empty folder from a newer clone. Dev-links mode edits the same files as the
git checkout—commit kit fixes from the repo, keep real data only under `~/pm-live`.

## 7. Optional verification stages (not assumed working)

Do these on non-sensitive data. Record pass/fail in `logs/setup-findings.md`.

1. **Workbench Clipper** (Chrome or Edge, ~2 minutes):
   1. Open `chrome://extensions` (Edge: `edge://extensions`).
   2. Turn on **Developer mode** (top right).
   3. **Load unpacked** → choose either  
      `~/pm-live/tools/workbench-clipper`  
      (same files via symlink) or  
      `<clone>/pm-workbench/tools/workbench-clipper`.
   4. After updating the extension, click **Reload** on that page (required — Chrome
      keeps the old menu until you do).
   5. Right-click a **public** page or Stream transcript → **Send to PM Workbench** →
      **Meeting notes / summary** (that path scrapes transcript entries in the DOM,
      text only — no screenshot; do not use **Selection only** for long meetings).
      Other categories may also save a viewport PNG. Files land in
      `~/Downloads/pm-workbench-inbox/<category>/`.
   6. From Claude Code in `~/pm-live`: `/capture process-inbox` (pulls clips out of
      Downloads, then processes them). Or one-shot: `python3 scripts/pull_clips.py`.
      Optional background watcher (`bash scripts/install_clip_watcher.sh`) needs macOS
      Full Disk Access — skip it unless you want auto-move without Claude.
2. **Claude in Chrome:** install per Anthropic; ask Claude Code to read one open
   public tab without clicking.
3. **Playwright MCP:** put `.mcp.json` only in the live folder with
   `npx --yes @playwright/mcp@latest` and a Chrome debug profile. Ask Claude Code
   to list tabs. Confirm click/type stay denied in `.claude/settings.json`.
4. **Scheduling:** `python3 scripts/run_scheduled.py daily-brief --dry-run`, then a
   hand run once `claude -p` works in that shell. Test `state/PAUSE`. Do not install
   cron until hand runs are reliable. `/loop` only in an open Claude Code session.
5. **Backup:** on the **isolated fixture only**, set `PM_STATE_BACKUP` to a
   non-git path outside the workbench and run `scripts/snapshot-state.sh`. Leave
   live backup unset until company storage is approved.
6. **Stubs / extract:** `log_metrics.py` and `render_template.py` still exit as
   stubs. `extract_document.sh` is live for common formats; on failure re-export
   or paste rather than retrying inventively.

## 8. Read next

- [START HERE](START%20HERE.md) — command menu and readiness table  
- [SETUP.md](SETUP.md) — browser, permissions, hooks  
- [CLAUDE.md](CLAUDE.md) — standing rules (fill only approved brackets)  
- [SCHEDULING.md](SCHEDULING.md) — unattended runs after manual success  
- [STATE-BACKUP.md](STATE-BACKUP.md) — approved backup destinations only  
