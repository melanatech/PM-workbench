# Shared prototype package (`prototypes/_shared/`)

**Status:** implemented (live-only). Soft catalog remains for one-off pieces not yet promoted.

## Goal

One live-only package that feature prototypes depend on via npm `file:../_shared`, so Guardrails-clean tokens and primitives update in one place.

## Shape

```
~/pm-live/prototypes/
  _shared/                 # package name @pm-live/prototype-kit
    package.json
    src/
      theme/               # CSS variables / tokens + kit.css
      components/          # Drawer, HelpPopover, InfoTip, SortableTable, ScenarioGuide, …
      index.js             # public exports
  my-feature/              # depends on file:../_shared
```

- Lives in **live** (`~/pm-live`), never in the public kit git tree (no company markup in kit).
- Kit documents the convention; `prototype-build` wires the dependency when `_shared` exists.

## Agent rules

1. **If `prototypes/_shared/package.json` exists:** new **web** / **repo** prototypes add `"@pm-live/prototype-kit": "file:../_shared"`, import theme/kit CSS, and prefer kit primitives over soft-copy for matching pieces.
2. **Else:** soft-copy from `prototype-components.md` as before.
3. **Promotion:** when a catalog row has been copied ≥2 times, offer to move it into `_shared` and update dependents (ask the PM).
4. **QA:** harness boots each feature app; `_shared` is a dependency. Optionally add a tiny examples page later.
5. **Guardrails loop:** fix shared primitives in `_shared` **and** append `ux-guardrails-lessons.md` — that is how fixes propagate across prototypes (MCP does not remember).
6. **Non-goals:** do not replace company UI base (`repos/`); do not put `@ux/*` in the public kit; do not force static HTML prototypes onto npm; do not treat `_shared` as baseline “today” truth (still port from the PM’s product repo).

## Shareable handoff

| Path | When |
|---|---|
| **Static** prototype (`index.html`) | Single-file open in a browser — already supported |
| **React** `npm run build` → `dist/` | Zip or `npm run preview` for stakeholders with a static host |
| **React** optional `npm run share` | Single-file HTML (e.g. `vite-plugin-singlefile`) so recipients need not `npm install` |

See `prototype-build` skill Step 2 handoff notes.
