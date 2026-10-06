---
description: Competitive change scan - dated captures diffed against last run
argument-hint: [competitors, or blank for the watchlist]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Scan: $ARGUMENTS (default: all of `reference/competitive-watchlist.md` — competitor, product areas, optional seed URLs, last-reviewed date).

**URL policy:** Seed URLs on the watchlist are **optional**. The `competitive-capture-agent` discovers official pages with **`python3 scripts/web_search.py`** (client-side; works when Bedrock rejects native WebSearch), then **WebFetch**es those hits. Do not block the scan waiting for the PM to paste links. If the PM (or a prior capture) already listed URLs, pass them through as accelerators.

**Bedrock / proxy note:** Native Claude `WebSearch` often fails with *"Bedrock does not support the web_search tool"*. That is expected on Bedrock-backed Claude Code. The kit search script is the supported fix — not "ask the PM for URLs" and not "give up." Only BLOCK discovery if `web_search.py` itself cannot reach the network.

## Persistence rules (non-negotiable — fixes chat-only captures)

Competitive findings **must land on disk in the same run**. Asking "Should I create the competitive-log?" is a defect. Chat paste is not a register.

1. Before dispatch: `mkdir -p state/competitive outputs/monthly`.
2. Dispatch each competitor to `competitive-capture-agent`. The agent **writes** `state/competitive/YYYY-MM-DD-<slug>.md` itself (including BLOCKED stubs) and returns the path.
3. After each agent returns: **verify the file exists** (Read or `ls`). If the agent returned capture body **without** a written path, **you write** `state/competitive/YYYY-MM-DD-<slug>.md` immediately from that body — still no asking.
4. **In the same run**, append (or create) [`outputs/monthly/competitive-log.md`](outputs/monthly/competitive-log.md) with today's section: competitors scanned, paths to capture files, summary table, initiative cross-check, BLOCKED list. Show the path (rule 20).
5. Backfill discovered URLs into `reference/competitive-watchlist.md`.
6. Cross-check `registers/initiatives.csv` and note any initiative impact in the log.
7. Do **not** store a BLOCKED stub as a "baseline" in narrative — label it BLOCKED. Do **not** re-fetch a competitor solely because the prior run left text only in chat; if the PM pastes that text into `inbox/competitive/`, process it into `state/competitive/` then the log.

**In parallel**, dispatch `internal-docs-reader` for internal battlecards when that path is configured; skip silently if it is not.

**First run:** `reference/competitive-watchlist.md` ships empty. Ask who the competitors are and which **product areas** matter — **not** a mandatory URL list. Write the watchlist, then scan. Never scan a conjured competitor set.

## Scope discipline (do not collapse the log)

Customer evidence (e.g. EV-007 four-line sales/tax/fees/tips) may **prioritize** a section or a comparison table. It must **not** become the only question the competitive log answers when the watchlist or available research covers more (exports, payout reconciliation, pricing gates, mobile vs desktop, AI/analytics, accounting integrations, etc.).

- Structure `outputs/monthly/competitive-log.md` by **watchlist product areas** (and any durable research themes already in `reference/user-research/` or `archive/documents/`).
- Put the customer-specific question in its own clearly labeled subsection — not as the sole "Key question" for the whole scan.
- If market research is in scope for the run, fold its themes into the log as **second-hand / needs URL verification**, separate from live captures. Do not leave them only in a "reference context" footnote while the lead narrative stays one-gap-narrow.
- Never ask "Should I expand the log to cover X?" when X was already in the watchlist or the research you read this run — expand it in the same write.

**Fan-out (required).** After the log and captures exist, apply `.claude/workflows/_fan-out.md`: append competitive implications to every touched INIT- `notes`, fold new open questions into assumptions, update `current-priorities.md` only if leadership pressure genuinely moved, and end with the Surfaces updated block. Competitive insight must not live only in `competitive-log.md`.

