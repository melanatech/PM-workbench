# Debugging the Workbench Clipper (meeting transcripts)

## What usually goes wrong

Stream / SharePoint meeting transcripts are a **virtualized list**. Only a slice of
entries is in the DOM at once. Inspect shows this clearly:

- `id="sub-entry-171"`
- `aria-posinset="172"`
- `aria-setsize="364"` ← total entries in the transcript

Older clipper versions (`transcript_entries: 60` with no scroll) only read whatever
was mounted when you clicked — often ~5 minutes of speech. **Inspect cannot see
unmounted rows either**; scrolling is required to load them.

Clipper **v0.4.1+** scrolls via `scrollIntoView` on the last mounted entry (Stream’s
virtualizer often freezes `scrollHeight` mid-list) and keeps going until
`max_posinset` reaches `aria-setsize`. Leave the tab focused; a long meeting can
take up to a minute.

## Quick verify after a clip

1. `chrome://extensions` → PM Workbench Clipper → confirm version **0.4.1+** → **Reload**.
2. Open a Stream transcript → *Send to PM Workbench* → *Meeting notes / summary*.
   Wait — do not switch tabs until the count notification appears.
3. Open the `.md` in Downloads / inbox and check frontmatter:

| Field | Good | Problem |
|---|---|---|
| `extract_source` | `transcript_scroll` | `selection` or `page` |
| `max_posinset` | ≈ `aria_setsize` | much smaller than `aria_setsize` |
| `transcript_entries` | ≈ `aria_setsize` | much smaller (also check for nested-duplicate inflation) |
| `aria_setsize` | e.g. 364 | `0` (scroller not found) |
| `incomplete` | `false` | `true` |
| `scroll_passes` | grows with meeting length | stops early (e.g. 12) while incomplete |

4. Notification: `Clipped 360/364 transcript entries` is success; `INCOMPLETE` means retry or use Stream’s **Download** on the transcript panel.

## Manual DOM check (while the page is open)

In DevTools Console on the Stream tab:

```js
// How many entries exist vs how many are mounted right now?
const mounted = document.querySelectorAll('[id^="sub-entry-"]').length;
const setSize = document.querySelector('[aria-setsize]')?.getAttribute('aria-setsize');
console.log({ mounted, setSize });
```

If `mounted << setSize`, virtualization is active — a non-scrolling scraper will always truncate.

## Fallback if scroll still misses rows

Use the transcript panel’s **Download** control in Stream, drop the file in
`inbox/meetings/`, then `/capture process-inbox`.

## Do not use Selection only for long meetings

That path saves only the highlight and will stop wherever your selection ends.
