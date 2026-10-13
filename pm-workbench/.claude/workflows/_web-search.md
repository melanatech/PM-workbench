# Web search recipe — Bedrock-safe URL discovery + durable captures

Shared by `/discover competitive-scan`, `/discover explore-brief`,
`/build prd-package`, and any ad-hoc external grounding. Chat is not storage.

## Why this exists

Amazon Bedrock (and some proxies) reject Claude's native **WebSearch** tool
(*"Bedrock does not support the web_search tool"*). That is infrastructure, not
a reason to ask the PM for URLs or to invent links from training memory.

**Always discover URLs with the client-side script first:**

```bash
python3 scripts/web_search.py --json --max 8 "YOUR QUERY"
```

The script tries DuckDuckGo → **Startpage** → Bing, then optional Serper/Brave
API keys. Prefer specific queries (product + "help" / "support" / "docs") over
bare category nouns — still no API key required for usable hits. Native
`WebSearch` is optional if it works in-session — never stop after a Bedrock
failure; fall through to `web_search.py` immediately.

## Access path (order)

1. Seeds / prior capture URLs if the workflow already has them (accelerators).
2. `python3 scripts/web_search.py --json …` — primary discovery.
3. WebFetch (or Read of a prior clip) **only** those URLs.
4. If `web_search.py` fails (network exit 2): write a BLOCKED stub under the
   durable path below; do not guess URLs.
5. If fetch is empty / 403 / homepage stub: try another hit; mark UNVERIFIED.
6. Never treat unaudited model knowledge as a dated capture — label
   `[external::training]` instead.

Name the access path in any output that used the web (CLAUDE.md rule 21):
e.g. "via `scripts/web_search.py` then WebFetch (URL)".

## Durable captures — `state/web-search/`

Competitive competitor pages stay in `state/competitive/` (see
`competitive-capture-agent`). Everything else — problem landscape, category,
user research public sources, solution patterns — lands here:

```
state/web-search/YYYY-MM-DD-<slug>.md
```

Slug = topic or INIT short name (lowercase hyphens). Write **before** returning
to chat when the search was consequential (Tier 1).

### Required heading order

```
# <Topic> — YYYY-MM-DD
## Queries run
- (exact query strings)
## Problems
- findings + source URLs (or "none fetched")
## Market / category
- findings + source URLs
## Users
- findings + source URLs (public research, forums, help-community — not invented personas)
## Solutions
- findings + source URLs (help docs, launch posts, vendor pages — not fabricated in-app tours)
## Inferences
- labeled `[hypothesis: …]` only
## BLOCKED / UNVERIFIED
- what failed and why
```

Omit an axis section only when that axis was out of scope for the run; say so
in one line under the section rather than inventing content.

## Brief / PRD axes

For `/discover explore-brief` and `/build prd-package`, search (or refresh)
these four axes unless the PM scoped to fewer:

| Axis | What to look for |
|---|---|
| **Problems** | How the pain is described publicly; adjacent jobs; known failure modes |
| **Market / category** | Category framing, substitutes, pricing/packaging norms |
| **Users** | Who hits the problem (roles/segments in public sources — never invent named customers) |
| **Solutions** | How others solve it (docs, launches, open patterns) — stress-test concepts, don't copy |

Reuse a same-day capture for the same slug when queries would not change;
otherwise write a new dated file.

## Index + fan-out

After writing a capture that will feed a brief/PRD/strategy:

```bash
python3 scripts/analysis_index.py append --root <live> \
  --topic-key "<topic>" --path state/web-search/YYYY-MM-DD-<slug>.md \
  --kind web-search --as-of YYYY-MM-DD \
  --one-line "<one-line>" --primary-sources "<urls or queries>" \
  --initiative-ids "INIT-…" --source-workflow <workflow>
```

Also walk `_fan-out.md` surface 14 (`state/web-search/`). Competitive-only
runs still use surface 8 (`state/competitive/`).

## Anti-patterns (forbidden)

- Native WebSearch failure → ask PM for URLs or give up
- Inventing URL paths or in-app product tours
- Chat-only findings when a capture file should exist
- Treating web hits as stronger than internal evidence/registers (report conflicts; rule 8)
- Using web search as a substitute for `context_preflight` / workspace analysis
