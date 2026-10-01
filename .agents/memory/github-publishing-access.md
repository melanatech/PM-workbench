---
name: GitHub publishing access
description: Distinguish connector authorization, terminal credentials, and permission to update the published branch.
---

Treat GitHub connector authorization separately from terminal Git
authentication. Successful repository reads and Git object uploads do not prove
that the final branch-reference update will succeed.

**Why:** A connected account accepted repository reads, object creation, and a
no-op reference update while rejecting the actual fast-forward update. Normal
terminal pushes independently continued to fail authentication. The live OAuth
grant did not include workflow permission, and the connector's reauthorization
scope set did not offer it; the branch-update rejection itself was a generic
404, not an explicit missing-scope diagnostic.

**How to apply:** Before publishing commits containing GitHub Actions changes,
check the live permissions and available reauthorization scopes. Do not assume
reconnecting the same connector adds a scope it does not offer. Preserve
history, use a non-force update, and verify the live branch before claiming
publication or advancing the local remote-tracking reference. If publication
is rejected, report the observed blocker without claiming an unproven cause.