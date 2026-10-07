// PM Workbench Clipper — a human clicks, a markdown file lands in Downloads.
// Chrome's downloads API can only write under the browser Downloads folder.
// Stream/SharePoint transcripts are virtualized lists: only a window of
// entries exists in the DOM at once (see aria-setsize vs mounted nodes).
// Meeting capture scrolls that panel and accumulates entries by id.
// Walkthrough session: importScripts → walkthrough-session.js (Start/Mark/Stop).

importScripts('walkthrough-session.js');

const CATEGORIES = [
  ['discovery',   'Discovery signal (customer / support / feedback)'],
  ['competitive', 'Competitive'],
  ['meetings',    'Meeting notes / summary'],
  ['metrics',     'Metric / dashboard reading'],
  ['documents',   'Internal document'],
  ['captures',    'Just capture it (classify later)']
];

const PAGE_CHAR_LIMIT = 200000;

function rebuildMenus() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'pmwb-root',
      title: 'Send to PM Workbench',
      contexts: ['page', 'selection']
    });
    for (const [id, title] of CATEGORIES) {
      chrome.contextMenus.create({
        id: 'pmwb-' + id,
        parentId: 'pmwb-root',
        title,
        contexts: ['page', 'selection']
      });
    }
    chrome.contextMenus.create({
      id: 'pmwb-sel-sep',
      parentId: 'pmwb-root',
      type: 'separator',
      contexts: ['selection']
    });
    chrome.contextMenus.create({
      id: 'pmwb-sel-root',
      parentId: 'pmwb-root',
      title: 'Selection only (highlighted text)',
      contexts: ['selection']
    });
    for (const [id, title] of CATEGORIES) {
      chrome.contextMenus.create({
        id: 'pmwb-sel-' + id,
        parentId: 'pmwb-sel-root',
        title,
        contexts: ['selection']
      });
    }
    chrome.contextMenus.create({
      id: 'pmwb-shot-sep',
      parentId: 'pmwb-root',
      type: 'separator',
      contexts: ['page']
    });
    chrome.contextMenus.create({
      id: 'pmwb-shot-root',
      parentId: 'pmwb-root',
      title: 'Screenshot only (no page text)',
      contexts: ['page']
    });
    for (const [id, title] of CATEGORIES) {
      chrome.contextMenus.create({
        id: 'pmwb-shot-' + id,
        parentId: 'pmwb-shot-root',
        title,
        contexts: ['page']
      });
    }
    if (typeof wtAppendMenus === 'function') {
      wtAppendMenus();
    }
  });
}

chrome.runtime.onInstalled.addListener(rebuildMenus);
chrome.runtime.onStartup.addListener(rebuildMenus);
rebuildMenus();
if (typeof wtWireWalkthrough === 'function') {
  wtWireWalkthrough();
}

// Runs in the page. Async: may scroll a virtualized transcript panel.
async function extractPagePayload() {
  const LIMIT = 200000;
  const links = [];
  const seenHref = new Set();

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function pushLinks(root) {
    for (const a of Array.from((root || document).querySelectorAll('a[href]'))) {
      const href = a.href || a.getAttribute('href') || '';
      if (!href || href.startsWith('javascript:') || seenHref.has(href)) continue;
      seenHref.add(href);
      const label = (a.innerText || a.getAttribute('aria-label') || href)
        .trim().replace(/\s+/g, ' ').slice(0, 120);
      links.push({ href, label });
      if (links.length >= 80) break;
    }
  }

  // Prefer Stream's stable ids. Fall back to aria-posinset so we don't
  // double-count a parent listitem wrapping the same sub-entry.
  function entryKey(el) {
    if (el.id && el.id.startsWith('sub-entry-')) return el.id;
    if (el.querySelector && el.querySelector('[id^="sub-entry-"]')) return '';
    const pos = el.getAttribute('aria-posinset');
    if (pos) return 'pos-' + pos;
    return '';
  }

  function collectEntries(into) {
    const nodes = document.querySelectorAll('[id^="sub-entry-"], [role="listitem"][aria-posinset]');
    for (const el of nodes) {
      const key = entryKey(el);
      if (!key || into.has(key)) continue;
      const line = (el.innerText || '').trim().replace(/\s+/g, ' ');
      if (line.length < 8 || line.length > 20000) continue;
      into.set(key, line);
    }
  }

  function readSetSize() {
    const el = document.querySelector(
      '[id^="sub-entry-"][aria-setsize], [role="listitem"][aria-setsize]'
    );
    if (!el) return 0;
    const n = parseInt(el.getAttribute('aria-setsize') || '0', 10);
    return Number.isFinite(n) ? n : 0;
  }

  function maxPosInset() {
    let max = 0;
    for (const el of document.querySelectorAll('[aria-posinset]')) {
      const n = parseInt(el.getAttribute('aria-posinset') || '0', 10);
      if (n > max) max = n;
    }
    // sub-entry-N is 0-based in Stream; treat id+1 as a pos if present
    for (const el of document.querySelectorAll('[id^="sub-entry-"]')) {
      const n = parseInt(String(el.id).replace(/\D/g, ''), 10);
      if (Number.isFinite(n) && n + 1 > max) max = n + 1;
    }
    return max;
  }

  function lastMountedEntry() {
    const nodes = document.querySelectorAll('[id^="sub-entry-"], [role="listitem"][aria-posinset]');
    let best = null;
    let bestPos = -1;
    for (const el of nodes) {
      let pos = parseInt(el.getAttribute('aria-posinset') || '', 10);
      if (!Number.isFinite(pos) && el.id) {
        const n = parseInt(String(el.id).replace(/\D/g, ''), 10);
        if (Number.isFinite(n)) pos = n + 1;
      }
      if (Number.isFinite(pos) && pos >= bestPos) {
        bestPos = pos;
        best = el;
      }
    }
    return best;
  }

  function findScrollParent(start) {
    // Prefer the nearest overflow ancestor that actually scrolls; Stream's
    // virtual list often reports a short scrollHeight until rows mount.
    let el = start;
    let fallback = null;
    while (el && el !== document.body && el !== document.documentElement) {
      const style = window.getComputedStyle(el);
      const oy = style.overflowY;
      if (oy === 'auto' || oy === 'scroll' || oy === 'overlay') {
        if (el.scrollHeight > el.clientHeight + 20) return el;
        if (!fallback) fallback = el;
      }
      el = el.parentElement;
    }
    return fallback;
  }

  function sortEntryKeys(keys) {
    return keys.sort((a, b) => {
      const na = parseInt(String(a).replace(/\D/g, ''), 10);
      const nb = parseInt(String(b).replace(/\D/g, ''), 10);
      if (Number.isFinite(na) && Number.isFinite(nb) && !(na === 0 && nb === 0 && a === b)) {
        if (na !== nb) return na - nb;
      }
      return String(a).localeCompare(String(b));
    });
  }

  async function advanceScroller(scroller, pass) {
    const step = Math.max(Math.floor(scroller.clientHeight * 0.55), 80);
    const last = lastMountedEntry();
    // Primary: scroll the last mounted row into view — this is what forces
    // Stream's virtualizer to mount the next window when scrollHeight stalls.
    if (last && typeof last.scrollIntoView === 'function') {
      try {
        last.scrollIntoView({ block: 'end', inline: 'nearest' });
      } catch (e) {
        try { last.scrollIntoView(false); } catch (e2) { /* ignore */ }
      }
    }
    // Also nudge the scroll container; virtual lists sometimes need both.
    const beforeTop = scroller.scrollTop;
    scroller.scrollTop = Math.min(scroller.scrollTop + step, scroller.scrollHeight);
    if (scroller.scrollTop === beforeTop) {
      scroller.scrollTop = scroller.scrollHeight;
    }
    // Every few stalled-looking passes, PageDown on the focused panel.
    if (pass % 5 === 4) {
      try {
        scroller.focus({ preventScroll: true });
        scroller.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'PageDown', code: 'PageDown', keyCode: 34, which: 34, bubbles: true
        }));
      } catch (e) { /* ignore */ }
    }
  }

  // --- Prefer Stream-style transcript: scroll virtualized list, accumulate ---
  const sample = document.querySelector('[id^="sub-entry-"], [role="listitem"][aria-posinset]');
  let setSize = readSetSize();
  let scrollPasses = 0;
  let maxPos = 0;
  let incomplete = false;
  const byKey = new Map();

  if (sample) {
    const scroller = findScrollParent(sample);
    collectEntries(byKey);
    setSize = setSize || readSetSize();
    maxPos = Math.max(maxPos, maxPosInset());

    if (scroller) {
      const startTop = scroller.scrollTop;
      scroller.scrollTop = 0;
      await sleep(200);
      collectEntries(byKey);
      setSize = Math.max(setSize, readSetSize());
      maxPos = Math.max(maxPos, maxPosInset());

      // Cap by expected size: ~3 passes per entry is plenty; never under 80.
      const maxPasses = setSize
        ? Math.min(Math.max(setSize * 3, 120), 900)
        : 400;
      // Only give up after a long stall *and* we can't advance posinset.
      const stallLimit = setSize ? 40 : 18;
      let stallRounds = 0;
      let lastSize = byKey.size;
      let lastMaxPos = maxPos;

      for (let i = 0; i < maxPasses; i++) {
        scrollPasses = i + 1;
        await advanceScroller(scroller, i);
        // Stream needs time to mount after scrollIntoView; wait longer when stalled.
        await sleep(stallRounds > 0 ? 180 : 110);
        collectEntries(byKey);
        setSize = Math.max(setSize, readSetSize());
        maxPos = Math.max(maxPos, maxPosInset());

        const reached = setSize > 0 && maxPos >= setSize && byKey.size >= Math.floor(setSize * 0.95);
        if (reached) break;

        const grew = byKey.size > lastSize || maxPos > lastMaxPos;
        if (grew) {
          stallRounds = 0;
          lastSize = byKey.size;
          lastMaxPos = maxPos;
        } else {
          stallRounds += 1;
          // Hard nudge: jump near end of current scrollHeight, wait, collect.
          if (stallRounds === 8 || stallRounds === 16) {
            scroller.scrollTop = 0;
            await sleep(150);
            collectEntries(byKey);
            scroller.scrollTop = scroller.scrollHeight;
            const last = lastMountedEntry();
            if (last) {
              try { last.scrollIntoView({ block: 'end' }); } catch (e) { /* ignore */ }
            }
            await sleep(250);
            collectEntries(byKey);
            setSize = Math.max(setSize, readSetSize());
            maxPos = Math.max(maxPos, maxPosInset());
            if (byKey.size > lastSize || maxPos > lastMaxPos) {
              stallRounds = 0;
              lastSize = byKey.size;
              lastMaxPos = maxPos;
              continue;
            }
          }
          if (stallRounds >= stallLimit) break;
        }
      }

      try { scroller.scrollTop = startTop; } catch (e) { /* ignore */ }
    } else {
      collectEntries(byKey);
      maxPos = Math.max(maxPos, maxPosInset());
    }

    if (byKey.size >= 3) {
      const keys = sortEntryKeys([...byKey.keys()]);
      const parts = [];
      const seenText = new Set();
      for (const k of keys) {
        const line = byKey.get(k);
        if (!line || seenText.has(line)) continue;
        if ([...seenText].some((s) => s.includes(line) && s.length > line.length + 10)) continue;
        seenText.add(line);
        parts.push(line);
      }
      const text = parts.join('\n\n').slice(0, LIMIT);
      // Incomplete if we never reached the last posinset Stream advertised.
      incomplete = !!(setSize && (maxPos < setSize || byKey.size < Math.floor(setSize * 0.9)));
      pushLinks(document);
      return {
        text,
        links,
        source: 'transcript_scroll',
        entry_count: byKey.size,
        aria_setsize: setSize || 0,
        max_posinset: maxPos,
        scroll_passes: scrollPasses,
        incomplete,
        truncated_chars: text.length >= LIMIT
      };
    }
  }

  // --- Fallback: plain page text ---
  const root = document.querySelector(
    '[data-tid="transcript-panel"], [aria-label*="Transcript" i], main, article, [role="main"]'
  ) || document.body;
  const text = (root && root.innerText ? root.innerText : '').slice(0, LIMIT);
  pushLinks(root);
  return {
    text,
    links,
    source: 'page',
    entry_count: 0,
    aria_setsize: setSize || 0,
    max_posinset: maxPos,
    scroll_passes: 0,
    incomplete: false,
    truncated_chars: text.length >= LIMIT
  };
}

async function captureVisiblePng(tabId) {
  try {
    if (tabId != null) {
      await chrome.tabs.update(tabId, { active: true });
    }
    const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' });
    return dataUrl || null;
  } catch (e) {
    return null;
  }
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const id = info.menuItemId;
  if (
    typeof id !== 'string'
    || !id.startsWith('pmwb-')
    || id === 'pmwb-root'
    || id === 'pmwb-sel-root'
    || id === 'pmwb-sel-sep'
    || id === 'pmwb-shot-root'
    || id === 'pmwb-shot-sep'
    || id === 'pmwb-wt-sep'
  ) {
    return;
  }

  if (typeof wtHandleMenu === 'function' && await wtHandleMenu(id, tab)) {
    return;
  }

  const selectionOnly = id.startsWith('pmwb-sel-');
  const screenshotOnly = id.startsWith('pmwb-shot-');
  const category = selectionOnly
    ? id.slice('pmwb-sel-'.length)
    : screenshotOnly
      ? id.slice('pmwb-shot-'.length)
      : id.slice('pmwb-'.length);
  if (!CATEGORIES.some(([c]) => c === category)) return;

  let body = '';
  let links = [];
  let captureKind = 'page';
  let extractSource = '';
  let entryCount = 0;
  let ariaSetSize = 0;
  let maxPosInset = 0;
  let scrollPasses = 0;
  let incomplete = false;
  const selection = (info.selectionText || '').trim();

  if (screenshotOnly) {
    body = '_(Screenshot only — see sibling PNG; no page text captured.)_';
    captureKind = 'screenshot';
    extractSource = 'viewport_png';
  } else if (selectionOnly) {
    body = selection;
    captureKind = 'selection';
  } else if (tab && tab.id) {
    try {
      // Meeting captures can take tens of seconds while the panel scrolls.
      if (chrome.notifications && chrome.notifications.create && category === 'meetings') {
        chrome.notifications.create('pmwb-scroll-' + Date.now(), {
          type: 'basic',
          iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
          title: 'PM Workbench',
          message: 'Scrolling transcript… leave this tab open; may take up to a minute.'
        });
      }
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractPagePayload
      });
      body = (result && result.text) || '';
      links = (result && result.links) || [];
      extractSource = (result && result.source) || '';
      entryCount = (result && result.entry_count) || 0;
      ariaSetSize = (result && result.aria_setsize) || 0;
      maxPosInset = (result && result.max_posinset) || 0;
      scrollPasses = (result && result.scroll_passes) || 0;
      incomplete = !!(result && result.incomplete);
      captureKind = (extractSource === 'transcript_scroll' || extractSource === 'transcript_entries')
        ? 'transcript'
        : 'page';
      if (category === 'discovery' && selection && selection.length < 4000
          && body.length > Math.max(8000, selection.length * 4)) {
        body = selection;
        captureKind = 'selection';
        links = [];
        incomplete = false;
      } else if (selection && selection.length > 40 && captureKind !== 'selection'
                 && !body.includes(selection.slice(0, 80))) {
        body = '## Highlighted excerpt\n\n' + selection + '\n\n## Full capture\n\n' + body;
      }
    } catch (e) {
      body = selection || '(page text could not be read — paste it manually)';
      captureKind = selection ? 'selection' : 'page_failed';
    }
  } else if (selection) {
    body = selection;
    captureKind = 'selection';
  }

  const now = new Date();
  const stamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const slug = (tab && tab.title ? tab.title : 'capture')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 50);

  const truncated = body.length >= PAGE_CHAR_LIMIT;
  const linkLines = links.length
    ? ['', '## Links on page', ...links.map((l) => `- [${l.label.replace(/[\[\]]/g, '')}](${l.href})`)]
    : [];

  let screenshotName = '';
  let screenshotDataUrl = null;
  if (
    tab
    && tab.windowId != null
    && (
      screenshotOnly
      || (category !== 'meetings' && captureKind !== 'selection')
    )
  ) {
    screenshotDataUrl = await captureVisiblePng(tab.id);
    if (screenshotDataUrl) {
      screenshotName = `${stamp}-${slug}.png`;
    }
  }
  if (screenshotOnly && !screenshotDataUrl) {
    if (chrome.notifications && chrome.notifications.create) {
      chrome.notifications.create('pmwb-shot-fail-' + Date.now(), {
        type: 'basic',
        iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
        title: 'PM Workbench',
        message: 'Screenshot failed — tab may be restricted. No file written.'
      });
    }
    return;
  }

  const md = [
    '---',
    `captured: ${now.toISOString()}`,
    `category: ${category}`,
    `source_url: ${info.pageUrl || (tab && tab.url) || ''}`,
    `title: ${(tab && tab.title || '').replace(/\n/g, ' ')}`,
    `capture_kind: ${captureKind}`,
    `extract_source: ${extractSource || captureKind}`,
    `transcript_entries: ${entryCount}`,
    `aria_setsize: ${ariaSetSize}`,
    `max_posinset: ${maxPosInset}`,
    `scroll_passes: ${scrollPasses}`,
    `incomplete: ${incomplete}`,
    `includes_images: ${screenshotName ? 'viewport_png' : 'false'}`,
    `screenshot: ${screenshotName || ''}`,
    `char_count: ${body.length}`,
    `truncated: ${truncated}`,
    'access_path: PM Workbench Clipper — read from the page the PM was viewing in a logged-in browser; not fetched by the model',
    'landing: ~/Downloads/pm-workbench-inbox/ (Chrome downloads API); pull via Claude Code process-inbox or python3 scripts/pull_clips.py',
    '---',
    '',
    body,
    ...linkLines
  ].join('\n');

  const mdUrl = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(md);
  const mdFile = `pm-workbench-inbox/${category}/${stamp}-${slug}.md`;

  chrome.downloads.download(
    { url: mdUrl, filename: mdFile, saveAs: false, conflictAction: 'uniquify' },
    (downloadId) => {
      if (screenshotDataUrl && screenshotName) {
        chrome.downloads.download({
          url: screenshotDataUrl,
          filename: `pm-workbench-inbox/${category}/${screenshotName}`,
          saveAs: false,
          conflictAction: 'uniquify'
        });
      }
      let note;
      if (captureKind === 'screenshot') {
        note = 'Screenshot only (PNG + stub markdown).';
      } else if (captureKind === 'selection') {
        note = 'Clipped selection only.';
      } else if (captureKind === 'transcript') {
        note = incomplete
          ? `Clipped ${entryCount} entries (pos ${maxPosInset}/${ariaSetSize || '?'}) — INCOMPLETE. Retry or use Stream Download.`
          : `Clipped ${entryCount} entries (pos ${maxPosInset}${ariaSetSize ? '/' + ariaSetSize : ''}, ${scrollPasses} passes).`;
      } else {
        note = 'Clipped page text.';
      }
      if (chrome.notifications && chrome.notifications.create) {
        chrome.notifications.create('pmwb-' + String(downloadId || Date.now()), {
          type: 'basic',
          iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
          title: 'PM Workbench',
          message: note
        });
      }
    }
  );
});
