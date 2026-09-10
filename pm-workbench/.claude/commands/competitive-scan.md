---
description: Competitive change scan - dated captures diffed against last run
argument-hint: [competitors, or blank for the watchlist]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Scan: $ARGUMENTS (default: all of `reference/competitive-watchlist.md` — competitor, product areas, pricing/release-notes/docs/positioning URLs, review sites, last-reviewed date).

Dispatch each competitor's watchlist entry to the `competitive-capture-agent` subagent — it fetches, diffs against the prior capture, and classifies changes, keeping several sites' worth of scraped copy out of this session. **In parallel, dispatch `internal-docs-reader`** to check for internally maintained battlecards or competitive analysis docs on the shared drive/Confluence — sales and marketing often keep these independently, and they're worth reconciling against what the external capture found. Collect all outputs into one change report.
5. **Cross-check against `registers/initiatives.csv`:** if a competitive move undermines an assumption behind something at prd/prototype/experiment stage, flag it against that specific initiative by name, not just as a general strategic note.
6. Append to `outputs/monthly/competitive-log.md`; flag anything urgent enough not to wait for the monthly cycle; feed strategic implications to /strategy-refresh.

**First run:** `reference/competitive-watchlist.md` ships empty. Ask who the competitors are and which of their pages matter (pricing, release notes, docs), write the watchlist, then scan. Never scan a conjured competitor set.
