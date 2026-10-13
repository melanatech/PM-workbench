# Deferred: shared prototype package (`prototypes/_shared/`)

**Status:** not implemented. Soft reuse via [`prototype-components.md`](prototype-components.md) is the current path.  
**Do this later** when copy-drift across greenfield demos becomes painful (same shell/table rebuilt 3+ times).

## Goal

One live-only package that feature prototypes depend on via npm `file:` (or a workspace), so tokens and primitives update in one place.

## Shape (recommended)

```
~/pm-live/prototypes/
  _shared/                 # package name e.g. @pm-live/prototype-kit
    package.json
    src/
      theme/               # CSS variables / tokens
      components/          # PageShell, StatGrid, DataTable primitives, etc.
      index.js             # public exports
  my-feature/              # depends on file:../_shared
  other-feature/
```

- Lives in **live** (`~/pm-live`), never in the public kit git tree (no company markup in kit).
- Kit only documents the convention + teaches `prototype-build` to wire the dependency.

## Implementation checklist (when picked up)

1. **Scaffold `_shared`** in live: minimal package.json (`name`, `main`/`exports`, no private registry required), theme tokens, 2–4 primitives you already copy from the catalog.
2. **Kit docs:** NEW-USER-SETUP §2a or new §2c — when `_shared` exists, new web/repo prototypes add:
   `"@pm-live/prototype-kit": "file:../_shared"` (or the chosen name) and import from it.
3. **`prototype-build` Step 0/2:** if `prototypes/_shared/package.json` exists, prefer linking it over soft-copy for matching primitives; still read `prototype-components.md` for feature-specific pieces not yet promoted.
4. **Promotion rule:** when a catalog row has been copied ≥2 times, offer to move it into `_shared` and update dependents (Tier 2 / ask PM).
5. **QA:** harness still boots each feature app; `_shared` is a dependency, not a separately demoed app (unless you add a tiny story page later).
6. **Checkpoints:** `prototype_checkpoint.py` stays per-feature; optionally checkpoint `_shared` when it changes.
7. **EVOLVING.md:** changelog that soft catalog remains for one-off pieces; `_shared` is the shared muscle.
8. **Non-goals:** do not replace company UI base (`repos/` symlink); do not put UXCore/private packages in the public kit; do not force static/loose HTML prototypes onto npm.

## Trigger to start

Soft catalog has several rows and you feel copy-paste drift — or you are about to build a third report-style prototype that needs the same shell.
