---
description: Learn a product flow end-to-end - UI walkthrough, doc comparison, metric map
argument-hint: [workflow, e.g. "refund flow"]
---

Deep-dive: $ARGUMENTS

1. **Walk the flow** via browser in the product ([PRODUCT_URL]) — I'll drive or you navigate read-only with me watching. Record every screen, decision point, and error state encountered.
2. **Compare against the paper trail — dispatch to `internal-docs-reader`** for Confluence docs, Jira tickets, and any shared-drive/file-browser design or architecture docs for this flow, so that reading happens off to the side while you keep walking the live product. The gaps and contradictions between actual behavior and documentation are the primary finding — list each one.
3. **Map to data:** which dashboard metrics and behavior-analytics segments cover this flow; which steps are dark (no instrumentation).
4. Output to `learning/[flow]/`: flow walkthrough w/ states; doc-vs-reality differences; metric map; likely bottlenecks worth validating; open questions.
5. Append to inventories in `reference/product-knowledge/`: feature-inventory.md, flow-inventory.md, data-dictionary.md — create on first run.

Pairs with `/code-dive` for the same area: UI truth + code truth + doc claims, three-way reconciled.

**First run:** ask for the product URL and the login path if the bracket is unfilled; save it.
