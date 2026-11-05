# Debugging the Workbench Clipper (meeting transcripts)

## What usually goes wrong

Stream / SharePoint meeting transcripts are a **virtualized list**. Only a slice of
entries is in the DOM at once. Inspect shows this clearly:

- `id="entry-N"` `role="group"` `aria-label="Speaker N minutes M seconds"`
- child `id="sub-entry-N"` `role="listitem"`
- `aria-posinset="172"`
- `aria-setsize="364"` ← total entries in the transcript

Older clipper versions only read whatever was mounted when you clicked, or scrolled
in large jumps (`scrollIntoView` + 55% steps) and stopped at ~95% coverage — rows
were skipped and speakers were lost.

**Clipper v0.6.1** scrolls the transcript (~28% of the panel per step) and does
**not** stop when the scroll position sticks at the current scroll height.
A virtualized list reports that height before the real end. While rows are
missing, a stuck position steps back, sends a wheel event, and continues if
the height or the row count grows. It gives up only after eight probes that
grow neither. Holes are then jumped to by position, not by looking up rows
that are not in the page. `incomplete: false` only when every position from
1..`aria_setsize` was collected. Leave the tab focused; a long meeting can
take a few minutes. Reload the extension or Chrome keeps 0.6.0 and the old stop.

**Encrypted CDN payload:** Stream fetches `/cdnmedia/transcripts` encrypted
(`kid` key ID). The clipper does **not** decrypt that response. Supported path =
displayed DOM text. If Download is enabled, drop a `.vtt`/`.docx` in `inbox/meetings/`.

## Quick verify after a clip

1. `chrome://extensions` → PM Workbench Clipper → confirm version **0.6.1** → **Reload**.
2. Open a Stream transcript → *Send to PM Workbench* → *Meeting notes / summary*.
   Wait — do not switch tabs until the count notification appears.
3. Open the `.md` in Downloads / inbox and check frontmatter:

| Field | Good | Problem |
|---|---|---|
| `extract_source` | `transcript_scroll` | `selection` or `page` |
| `transcript_entries` | = `aria_setsize` | smaller |
| `max_posinset` | = `aria_setsize` | much smaller |
| `aria_setsize` | e.g. 278 | `0` (scroller not found) |
| `incomplete` | `false` | `true` |
| `missing_posinset` | empty | comma-separated gaps |
| `speakers` | `["Name",…]` | `[]` on a multi-speaker meeting |
| `scroll_passes` | grows with meeting length | stops early while incomplete |

4. Notification: `Clipped 278/278 entries` is success; `INCOMPLETE` means reload the
   extension and recapture (or use Stream **Download** if enabled).

## Manual DOM check (while the page is open)

In DevTools Console on the Stream tab:

```js
const mounted = document.querySelectorAll('[id^="sub-entry-"]').length;
const setSize = document.querySelector('[aria-setsize]')?.getAttribute('aria-setsize');
const sample = document.querySelector('[id^="entry-"][role="group"]')?.getAttribute('aria-label');
console.log({ mounted, setSize, sample });
```

If `mounted << setSize`, virtualization is active — a non-scrolling scraper will always truncate.

## Fallback if scroll still misses rows

1. Confirm version **0.6.1** and that the extension was reloaded, then recapture.
2. Teams blocks `.vtt` download when you are not the meeting owner. Do not use a transcript download as the plan for those meetings.
3. Do **not** decrypt `/cdnmedia/transcripts`.

## Do not use Selection only for long meetings

That path saves only the highlight and will stop wherever your selection ends.

## Walkthrough recorder (v0.5.0+)

| Symptom | Check |
|---|---|
| No Start/Mark/Stop menus | Reload extension; confirm version **0.5.0+** on `chrome://extensions` |
| REC badge but no steps in Downloads | Restricted page (`chrome://`)? Screenshot fails — try an https product tab |
| Only top of long page | Viewport-only API — scroll, then **Mark step**; scroll-settle also snaps if you moved >~40% viewport |
| Service worker “asleep” mid-walk | Alarms keep session; if events stop, Mark step once or Stop & save — state is in `chrome.storage` |
| Playwright still failing SSO | Expected — use walkthrough in daily Chrome instead of the automation profile |

After Stop, expect under `~/Downloads/pm-workbench-inbox/walkthroughs/`:

- `<stem>.md`
- `<stem>.events.jsonl`
- `<stem>.step-01.png` …
