---
name: Filesystem preflight
description: Fail-closed validation when shell tools enumerate recovery data.
---

Do not rely on `set -e` to propagate failures from a `find` command inside
process substitution. Build a complete manifest with a checked exit status
before making any recovery writes, and reuse that manifest for validation and
copying.

**Why:** A permission-denied snapshot subtree can make `find` emit only a
partial list while a surrounding restore loop exits successfully. That creates
an incomplete recovery even though preflight appeared to finish.

**How to apply:** When changing snapshot restore or other filesystem recovery
tools, fail closed on enumeration and read errors. Test that a traversal failure
leaves the destination untouched, not just that ordinary conflicts are refused.