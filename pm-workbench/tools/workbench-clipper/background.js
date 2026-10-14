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

  // Stream transcript: each row is
  //   div[id^=entry-N][role=group][aria-label="Speaker N minutes M seconds"]
  //   └─ div[id^=sub-entry-N][role=listitem][aria-posinset][aria-setsize]
  // Class hashes (baseEntry-484) change between builds — use id/ARIA only.

  const DURATION_RE = /\s+(?:(\d+)\s+hours?\s+)?(?:(\d+)\s+minutes?\s+)?(\d+)\s+seconds?\s*$/i;

  function parseSpeakerLabel(label) {
    if (!label) return { speaker: '', time: '' };
    const m = label.match(DURATION_RE);
    if (!m) return { speaker: label.trim(), time: '' };
    const speaker = label.slice(0, m.index).trim();
    const h = parseInt(m[1] || '0', 10);
    const min = parseInt(m[2] || '0', 10);
    const sec = parseInt(m[3] || '0', 10);
    const time = h > 0
      ? `${h}:${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
      : `${min}:${String(sec).padStart(2, '0')}`;
    return { speaker, time };
  }

  function readRow(subEl) {
    const pos = parseInt(subEl.getAttribute('aria-posinset') || '', 10);
    if (!Number.isFinite(pos) || pos < 1) return null;
    const text = (subEl.innerText || '').trim().replace(/\s+/g, ' ');
    if (!text || text.length > 20000) return null;
    let speaker = '';
    let time = '';
    const group = subEl.closest('[id^="entry-"][role="group"]')
      || subEl.closest('[role="group"][aria-label]');
    if (group) {
      const parsed = parseSpeakerLabel(group.getAttribute('aria-label') || '');
      speaker = parsed.speaker;
      time = parsed.time;
    }
    if (!speaker) {
      const aria = subEl.parentElement
        && subEl.parentElement.querySelector('[id^="timestampSpeakerAriaLabel-"]');
      if (aria) {
        const parsed = parseSpeakerLabel((aria.textContent || '').trim());
        speaker = parsed.speaker;
        time = time || parsed.time;
      }
    }
    if (!speaker) {
      const item = subEl.closest('[id^="listItem-"]');
      const nameEl = item && item.querySelector('[id^="itemHeader-"] [class*="itemDisplayName"]');
      const tsEl = item && item.querySelector('[id^="Header-timestamp-"]');
      if (nameEl) speaker = (nameEl.textContent || '').trim();
      if (tsEl) time = (tsEl.textContent || '').trim();
    }
    const setSize = parseInt(subEl.getAttribute('aria-setsize') || '0', 10) || 0;
    return { pos, text, speaker, time, setSize };
  }

  function collectVisible(byPos) {
    const nodes = document.querySelectorAll('[id^="sub-entry-"][role="listitem"][aria-posinset]');
    let minPos = Infinity;
    let maxPos = 0;
    let setSize = 0;
    for (const el of nodes) {
      const row = readRow(el);
      if (!row) continue;
      if (!byPos.has(row.pos)) byPos.set(row.pos, row);
      if (row.pos < minPos) minPos = row.pos;
      if (row.pos > maxPos) maxPos = row.pos;
      if (row.setSize > setSize) setSize = row.setSize;
    }
    return {
      minPos: Number.isFinite(minPos) ? minPos : 0,
      maxPos,
      setSize,
      count: byPos.size
    };
  }

  function findScrollParent(start) {
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

  function waitForSettle(scroller, quietMs, maxMs) {
    return new Promise((resolve) => {
      let lastChange = Date.now();
      const start = Date.now();
      const obs = new MutationObserver(() => { lastChange = Date.now(); });
      try {
        obs.observe(scroller, { childList: true, subtree: true, characterData: true });
      } catch (e) { /* ignore */ }
      const tick = () => {
        const now = Date.now();
        if (now - lastChange >= quietMs || now - start >= maxMs) {
          try { obs.disconnect(); } catch (e) { /* ignore */ }
          resolve();
          return;
        }
        setTimeout(tick, 40);
      };
      setTimeout(tick, quietMs);
    });
  }

  function formatTranscript(byPos) {
    const positions = [...byPos.keys()].sort((a, b) => a - b);
    const parts = [];
    let prevSpeaker = null;
    let buf = [];
    let bufTime = '';
    const flush = () => {
      if (!buf.length) return;
      const head = prevSpeaker
        ? (bufTime ? `**${prevSpeaker}** [${bufTime}]: ` : `**${prevSpeaker}**: `)
        : '';
      parts.push(head + buf.join(' '));
      buf = [];
      bufTime = '';
    };
    for (const pos of positions) {
      const row = byPos.get(pos);
      if (!row) continue;
      if (row.speaker !== prevSpeaker) {
        flush();
        prevSpeaker = row.speaker || null;
        bufTime = row.time || '';
        buf = [row.text];
      } else {
        if (!bufTime && row.time) bufTime = row.time;
        buf.push(row.text);
      }
    }
    flush();
    return parts.join('\n\n');
  }

  function missingPositions(byPos, setSize) {
    if (!setSize) return [];
    const miss = [];
    for (let i = 1; i <= setSize; i++) {
      if (!byPos.has(i)) miss.push(i);
    }
    return miss;
  }

  async function slowScrollCapture(scroller, byPos) {
    const startTop = scroller.scrollTop;
    scroller.scrollTop = 0;
    await waitForSettle(scroller, 250, 2000);
    let stats = collectVisible(byPos);
    let setSize = stats.setSize;
    let scrollPasses = 0;
    let stallRounds = 0;
    let lastCount = byPos.size;
    const maxPasses = setSize ? Math.min(Math.max(setSize * 2, 80), 600) : 300;

    while (scrollPasses < maxPasses) {
      scrollPasses += 1;
      const step = Math.max(Math.floor(scroller.clientHeight * 0.35), 48);
      const before = scroller.scrollTop;
      scroller.scrollTop = Math.min(before + step, scroller.scrollHeight);
      await waitForSettle(scroller, 250, 2000);
      stats = collectVisible(byPos);
      if (stats.setSize > setSize) setSize = stats.setSize;

      // Gap: lowest newly-visible pos jumped past what we have
      const haveMax = Math.max(0, ...byPos.keys());
      if (stats.minPos > haveMax + 1 && haveMax > 0) {
        scroller.scrollTop = Math.max(0, scroller.scrollTop - Math.floor(step * 0.5));
        await waitForSettle(scroller, 250, 2000);
        collectVisible(byPos);
      }

      if (setSize && byPos.size >= setSize && missingPositions(byPos, setSize).length === 0) {
        break;
      }
      if (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4
          && scroller.scrollTop === before) {
        stallRounds += 1;
        if (stallRounds >= 6) break;
      } else if (byPos.size > lastCount) {
        stallRounds = 0;
        lastCount = byPos.size;
      } else {
        stallRounds += 1;
        if (stallRounds >= 12) break;
      }
    }

    // Optional full-height fallback if still missing rows
    let missing = missingPositions(byPos, setSize);
    if (missing.length && setSize) {
      const prevH = scroller.style.height;
      const prevMax = scroller.style.maxHeight;
      try {
        scroller.style.height = scroller.scrollHeight + 'px';
        scroller.style.maxHeight = 'none';
        await waitForSettle(scroller, 300, 2500);
        collectVisible(byPos);
        for (const pos of missing.slice(0, 40)) {
          const el = document.querySelector(`[id^="sub-entry-"][aria-posinset="${pos}"]`);
          if (el && typeof el.scrollIntoView === 'function') {
            try { el.scrollIntoView({ block: 'center' }); } catch (e) { /* ignore */ }
            await waitForSettle(scroller, 200, 1500);
            collectVisible(byPos);
          }
        }
      } finally {
        scroller.style.height = prevH;
        scroller.style.maxHeight = prevMax;
      }
      missing = missingPositions(byPos, setSize);
    }

    try { scroller.scrollTop = startTop; } catch (e) { /* ignore */ }
    return { setSize, scrollPasses, missing };
  }

  // --- Prefer Stream-style transcript: slow overlapping scroll ---
  const sample = document.querySelector('[id^="sub-entry-"][role="listitem"][aria-posinset]');
  const byPos = new Map();
  let setSize = 0;
  let scrollPasses = 0;
  let maxPos = 0;
  let incomplete = false;
  let missing = [];
  let speakers = [];

  if (sample) {
    const scroller = findScrollParent(sample);
    collectVisible(byPos);
    if (scroller) {
      const result = await slowScrollCapture(scroller, byPos);
      setSize = result.setSize;
      scrollPasses = result.scrollPasses;
      missing = result.missing;
    } else {
      const st = collectVisible(byPos);
      setSize = st.setSize;
      missing = missingPositions(byPos, setSize);
    }
    maxPos = byPos.size ? Math.max(...byPos.keys()) : 0;
    incomplete = !!(setSize && missing.length > 0);
    const speakerSet = new Set();
    for (const row of byPos.values()) {
      if (row.speaker) speakerSet.add(row.speaker);
    }
    speakers = [...speakerSet];

    if (byPos.size >= 1) {
      const text = formatTranscript(byPos).slice(0, LIMIT);
      pushLinks(document);
      return {
        text,
        links,
        source: 'transcript_scroll',
        entry_count: byPos.size,
        aria_setsize: setSize || 0,
        max_posinset: maxPos,
        scroll_passes: scrollPasses,
        incomplete,
        missing_posinset: missing.slice(0, 80).join(','),
        speakers,
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
    missing_posinset: '',
    speakers: [],
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
  let missingPosinset = '';
  let speakers = [];
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
      // Meeting captures can take a few minutes — slow overlapping scroll.
      if (chrome.notifications && chrome.notifications.create && category === 'meetings') {
        chrome.notifications.create('pmwb-scroll-' + Date.now(), {
          type: 'basic',
          iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
          title: 'PM Workbench',
          message: 'Capturing transcript (slow scroll)… leave this tab open; may take a few minutes.'
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
      missingPosinset = (result && result.missing_posinset) || '';
      speakers = (result && result.speakers) || [];
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
    `missing_posinset: ${missingPosinset}`,
    `speakers: ${JSON.stringify(speakers)}`,
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
        const speakerNote = speakers.length ? `; speakers: ${speakers.slice(0, 6).join(', ')}${speakers.length > 6 ? '…' : ''}` : '';
        note = incomplete
          ? `Clipped ${entryCount}/${ariaSetSize || '?'} entries — INCOMPLETE (missing ${missingPosinset || 'rows'}). Reload clipper + recapture.`
          : `Clipped ${entryCount}${ariaSetSize ? '/' + ariaSetSize : ''} entries (${scrollPasses} passes${speakerNote}).`;
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
