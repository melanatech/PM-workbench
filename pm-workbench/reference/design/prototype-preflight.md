# Prototype preflight (durable — feed the next prototype)

A review in chat does not train the next session. Failures persist only if we
write them here (or into a prototype’s QA notes) and `/build prototype-build`
reads this file **before** scaffolding.

**Cross-prototype learning path:** when a failure is in a control that belongs in
`prototypes/_shared` (`@pm-live/prototype-kit`), fix the primitive **there** and
append a lesson row here in the same run. Feature apps pick up the fix on the
next `npm install` / link. See `shared-prototype-package.md`.

After a prototype UX failure: append dated rows below (theme → fix → where seen).
Before the next prototype build: apply every **Standing preflight** item that fits
the surface.

A company UX checker, if you have one, stays in `.claude/CLAUDE.local.md`. Do not
name it in this kit.

## Standing preflight (apply by default on web prototypes)

Use these unless the Feature Contract explicitly forbids them:

1. **Interactive affordances are buttons/links** with visible focus (`:focus-visible`), not clickable `<div>`s.
2. **Icon-only controls** need an accessible name (`aria-label` / visible text). Decorative icons: `aria-hidden="true"`.
3. **Tooltips / info**: do not rely on hover alone — support keyboard focus and/or click; Esc dismisses and restores focus.
4. **Dialogs / drawers**: `role="dialog"`, labelled title, focus trap or documented non-modal behavior, Esc closes, return focus to opener.
5. **Tables**: column headers `scope="col"`; sortable columns expose `aria-sort`; scroll regions named if needed.
6. **Live updates** (mode on, answer revealed): `role="status"` or `aria-live` as appropriate.
7. **Contrast**: body text and controls meet contrast on surface/background tokens; don’t put muted gray on muted gray for primary actions.
8. **Touch / narrow**: primary controls ≥ ~32–44px hit target; no critical UI only in hover; test ~390px width.
9. **States**: empty / loading / error / denied are real screens with roles (`alert` where needed), not blank pages.
10. **Prototype chrome** (variant switcher, Guide, Reset) is **out of product scope** for an accessibility check — render product DOM without that bar when checking (see `qa/render-snapshots.mjs` pattern).

## Lesson log (append-only)

| Date | Theme | Fix | Seen in |
|---|---|---|---|
| 2026-10-13 | Hover-only KPI info | Click + keyboard; Esc dismisses; labelled control | `prototypes/[feature]` (concept vs baseline) |
| 2026-10-13 | Side panel covering prototype controls | Non-modal side drawer starts below `--bar-h`; page shifts on wide screens | `prototypes/[feature]` |
| 2026-10-13 | Sort vs explain on header click | Explain mode uses separate explain targets; does not sort | `prototypes/[feature]` |
| 2026-10-13 | A check needs real HTML | Snapshot rendered DOM (product only) via Playwright before checking | `prototypes/[feature]/qa/render-snapshots.mjs` |
| 2026-10-13 | Shared kit as learning surface | Drawer / HelpPopover / InfoTip / ScenarioGuide live in `prototypes/_shared`; lessons + kit bump = inheritance | `@pm-live/prototype-kit` |

_Add rows when the same UX failure happens again — do not only fix in chat._
