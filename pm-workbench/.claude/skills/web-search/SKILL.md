---
name: web-search
description: >
  Use when the PM asks to search the web for product context, market/category,
  user problems, or how others solve something — or when explore-brief / PRD
  needs external grounding. Always uses scripts/web_search.py first (Bedrock-safe),
  writes state/web-search/, follows _web-search.md. Not a substitute for
  competitive-scan (competitors → state/competitive/).
---

# web-search

Plain-language entry for the shared **web search recipe**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path that skips durable capture).
2. Execute `.claude/workflows/_web-search.md` in full: `python3 scripts/web_search.py` first, then WebFetch, then write `state/web-search/YYYY-MM-DD-<slug>.md` with the Problems / Market / Users / Solutions heading order.
3. For a full competitor landscape, route to `/discover competitive-scan` instead (that workflow owns `state/competitive/` + the monthly log).
4. When the ask is part of a brief or PRD, prefer running `/discover explore-brief` or `/build prd-package` so Step 1.5 / 0.5 runs inside the workflow — do not invent a third parallel path.

Forbidden: native WebSearch-only on Bedrock; chat-only findings; inventing URLs or named customers from training.
