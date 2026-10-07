// Walkthrough session — Start / Mark step / Stop → Downloads package.
// Loaded via importScripts from background.js. Passive recording only.

const WT_MAX_STEPS = 40;
const WT_NAV_SETTLE_MS = 1000;
const WT_CLICK_SETTLE_MS = 400;
const WT_SCROLL_MIN_FRAC = 0.4;

const WT_STORAGE_KEY = 'pmwbWalkthrough';

let wtNavTimer = null;
let wtClickTimer = null;

function wtNotify(message) {
  if (chrome.notifications && chrome.notifications.create) {
    chrome.notifications.create('pmwb-wt-' + Date.now(), {
      type: 'basic',
      iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
      title: 'PM Workbench Walkthrough',
      message
    });
  }
}

async function wtGetSession() {
  const data = await chrome.storage.session.get(WT_STORAGE_KEY).catch(() => ({}));
  if (data && data[WT_STORAGE_KEY]) return data[WT_STORAGE_KEY];
  const local = await chrome.storage.local.get(WT_STORAGE_KEY).catch(() => ({}));
  return (local && local[WT_STORAGE_KEY]) || null;
}

async function wtSetSession(session) {
  const payload = { [WT_STORAGE_KEY]: session };
  try {
    await chrome.storage.session.set(payload);
  } catch (e) {
    await chrome.storage.local.set(payload);
  }
}

async function wtClearSession() {
  try {
    await chrome.storage.session.remove(WT_STORAGE_KEY);
  } catch (e) { /* */ }
  await chrome.storage.local.remove(WT_STORAGE_KEY);
}

function wtMakeStem(title) {
  const now = new Date();
  const stamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const slug = (title || 'walkthrough')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40) || 'walkthrough';
  return `${stamp}-${slug}`;
}

async function wtUpdateBadge(active) {
  if (!chrome.action) return;
  try {
    await chrome.action.setBadgeText({ text: active ? 'REC' : '' });
    await chrome.action.setBadgeBackgroundColor({ color: active ? '#b00020' : '#000000' });
    await chrome.action.setTitle({
      title: active
        ? 'PM Workbench — walkthrough recording (click to Stop & save)'
        : 'PM Workbench Clipper — click to Start walkthrough'
    });
  } catch (e) { /* */ }
}

async function wtInject(tabId) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['content-walkthrough.js']
    });
  } catch (e) {
    wtNotify('Could not inject recorder on this page (restricted URL?).');
    return false;
  }
  return true;
}

async function wtCapturePng(tabId) {
  try {
    if (tabId != null) {
      await chrome.tabs.update(tabId, { active: true });
    }
    return await chrome.tabs.captureVisibleTab(null, { format: 'png' });
  } catch (e) {
    return null;
  }
}

function wtDownload(url, filename) {
  return new Promise((resolve) => {
    chrome.downloads.download(
      { url, filename, saveAs: false, conflictAction: 'uniquify' },
      (id) => resolve(id)
    );
  });
}

async function wtAddStep(session, reason, tab) {
  if (!session || !session.active) return session;
  if ((session.steps || []).length >= WT_MAX_STEPS) {
    wtNotify(`Step cap (${WT_MAX_STEPS}) reached — Stop to save, or continue without new screenshots.`);
    return session;
  }
  const tabId = tab && tab.id != null ? tab.id : session.tabId;
  const png = await wtCapturePng(tabId);
  if (!png) {
    wtNotify('Screenshot failed for this step.');
    return session;
  }
  const n = (session.steps || []).length + 1;
  const nn = String(n).padStart(2, '0');
  const stepFile = `${session.stem}.step-${nn}.png`;
  await wtDownload(png, `pm-workbench-inbox/walkthroughs/${stepFile}`);

  let url = session.lastUrl || '';
  let title = session.lastTitle || '';
  let scrollY = session.lastScrollY || 0;
  try {
    const t = await chrome.tabs.get(tabId);
    url = t.url || url;
    title = t.title || title;
  } catch (e) { /* */ }

  const step = {
    n,
    reason,
    url,
    title,
    scrollY,
    file: stepFile,
    ts: new Date().toISOString()
  };
  session.steps = (session.steps || []).concat([step]);
  session.lastUrl = url;
  session.lastTitle = title;
  session.lastScrollSnapY = scrollY;
  session.events = (session.events || []).concat([{
    type: 'snapshot',
    ts: step.ts,
    reason,
    step: n,
    url,
    title,
    scrollY,
    file: stepFile
  }]);
  await wtSetSession(session);
  try {
    await chrome.alarms.create('pmwb-wt-keepalive', { delayInMinutes: 0.5 });
  } catch (e) { /* */ }
  return session;
}

async function wtStart(tab) {
  if (!tab || tab.id == null) {
    wtNotify('No active tab to record.');
    return;
  }
  const existing = await wtGetSession();
  if (existing && existing.active) {
    wtNotify('Walkthrough already recording — use Stop & save, or Mark step.');
    return;
  }
  const stem = wtMakeStem(tab.title);
  const session = {
    active: true,
    tabId: tab.id,
    startedAt: new Date().toISOString(),
    startUrl: tab.url || '',
    stem,
    events: [{
      type: 'session_start',
      ts: new Date().toISOString(),
      url: tab.url || '',
      title: tab.title || ''
    }],
    steps: [],
    lastUrl: tab.url || '',
    lastTitle: tab.title || '',
    lastScrollY: 0,
    lastScrollSnapY: 0
  };
  await wtSetSession(session);
  await wtUpdateBadge(true);
  const ok = await wtInject(tab.id);
  if (!ok) {
    await wtClearSession();
    await wtUpdateBadge(false);
    return;
  }
  wtNotify('Recording clicks + screenshots until you Stop. Scroll then Mark step for below-the-fold.');
  // Initial snap after settle
  setTimeout(async () => {
    const s = await wtGetSession();
    if (s && s.active) await wtAddStep(s, 'session_start', tab);
  }, WT_NAV_SETTLE_MS);
}

async function wtMark(tab) {
  const session = await wtGetSession();
  if (!session || !session.active) {
    wtNotify('No active walkthrough — Start first.');
    return;
  }
  const before = (session.steps || []).length;
  const updated = await wtAddStep(session, 'mark_step', tab || { id: session.tabId });
  const after = (updated && updated.steps) ? updated.steps.length : before;
  wtNotify(after > before ? `Marked step ${after}.` : 'Mark step failed or at cap — check notification.');
}

async function wtStop() {
  const session = await wtGetSession();
  if (!session || !session.active) {
    wtNotify('No active walkthrough.');
    return;
  }
  session.active = false;
  session.endedAt = new Date().toISOString();
  session.events = (session.events || []).concat([{
    type: 'session_end',
    ts: session.endedAt,
    step_count: (session.steps || []).length
  }]);

  const steps = session.steps || [];
  const events = session.events || [];
  const mdLines = [
    '---',
    `captured: ${session.endedAt}`,
    'category: walkthroughs',
    `source_url: ${session.startUrl || ''}`,
    `title: ${(session.lastTitle || 'walkthrough').replace(/\n/g, ' ')}`,
    'capture_kind: walkthrough',
    `stem: ${session.stem}`,
    `step_count: ${steps.length}`,
    `event_count: ${events.length}`,
    `started: ${session.startedAt}`,
    'includes_images: step_pngs',
    'access_path: PM Workbench Clipper walkthrough — recorded in the PM logged-in Chrome tab; not fetched by the model',
    'landing: ~/Downloads/pm-workbench-inbox/walkthroughs/; pull via process-inbox or python3 scripts/pull_clips.py',
    '---',
    '',
    `# Walkthrough — ${session.lastTitle || session.stem}`,
    '',
    `- **Start URL:** ${session.startUrl || ''}`,
    `- **Steps:** ${steps.length} (viewport PNGs; scroll + Mark step for below-the-fold)`,
    `- **Events:** see \`${session.stem}.events.jsonl\``,
    '',
    '## Timeline',
    ''
  ];
  for (const step of steps) {
    mdLines.push(`### Step ${step.n} — ${step.reason}`);
    mdLines.push('');
    mdLines.push(`- **URL:** ${step.url}`);
    mdLines.push(`- **Title:** ${step.title}`);
    mdLines.push(`- **scrollY:** ${step.scrollY}`);
    mdLines.push(`- **Screenshot:** [${step.file}](${step.file})`);
    mdLines.push(`- **When:** ${step.ts}`);
    mdLines.push('');
  }
  mdLines.push('## Event log (summary)');
  mdLines.push('');
  for (const ev of events.slice(0, 200)) {
    if (ev.type === 'snapshot') continue;
    const bit = ev.text || ev.field || ev.href || '';
    mdLines.push(`- \`${ev.ts}\` **${ev.type}** ${ev.url || ''} ${bit}`.trim());
  }
  mdLines.push('');

  const mdUrl = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(mdLines.join('\n'));
  await wtDownload(mdUrl, `pm-workbench-inbox/walkthroughs/${session.stem}.md`);

  const jsonl = events.map((e) => JSON.stringify(e)).join('\n') + '\n';
  const jsonUrl = 'data:application/x-ndjson;charset=utf-8,' + encodeURIComponent(jsonl);
  await wtDownload(jsonUrl, `pm-workbench-inbox/walkthroughs/${session.stem}.events.jsonl`);

  await wtClearSession();
  await wtUpdateBadge(false);
  try {
    await chrome.alarms.clear('pmwb-wt-keepalive');
  } catch (e) { /* */ }
  wtNotify(`Saved walkthrough (${steps.length} steps) to Downloads/pm-workbench-inbox/walkthroughs/`);
}

function wtScheduleNavSnap(tabId) {
  if (wtNavTimer) clearTimeout(wtNavTimer);
  wtNavTimer = setTimeout(async () => {
    const session = await wtGetSession();
    if (!session || !session.active) return;
    if (session.tabId != null && tabId !== session.tabId) return;
    await wtInject(tabId);
    await wtAddStep(session, 'nav_settle', { id: tabId });
  }, WT_NAV_SETTLE_MS);
}

function wtScheduleClickSnap(tabId) {
  if (wtClickTimer) clearTimeout(wtClickTimer);
  wtClickTimer = setTimeout(async () => {
    const session = await wtGetSession();
    if (!session || !session.active) return;
    await wtAddStep(session, 'click_settle', { id: tabId || session.tabId });
  }, WT_CLICK_SETTLE_MS);
}

function wtWireWalkthrough() {
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.source !== 'pmwb-walkthrough') return;
    (async () => {
      const session = await wtGetSession();
      if (!session || !session.active) {
        sendResponse({ ok: false });
        return;
      }
      const tabId = sender.tab && sender.tab.id;
      if (tabId != null) session.tabId = tabId;
      if (msg.url) session.lastUrl = msg.url;
      if (msg.title) session.lastTitle = msg.title;
      if (typeof msg.scrollY === 'number') session.lastScrollY = msg.scrollY;

      if (msg.type === 'ready') {
        await wtSetSession(session);
        sendResponse({ ok: true });
        return;
      }

      session.events = (session.events || []).concat([Object.assign({}, msg)]);
      await wtSetSession(session);

      if (msg.type === 'url') {
        wtScheduleNavSnap(tabId || session.tabId);
      } else if (msg.type === 'click') {
        // Snap after short settle; nav will also fire if URL changes
        wtScheduleClickSnap(tabId || session.tabId);
      } else if (msg.type === 'scroll') {
        const vh = msg.viewportH || 800;
        const last = session.lastScrollSnapY || 0;
        const y = msg.scrollY || 0;
        if (Math.abs(y - last) >= vh * WT_SCROLL_MIN_FRAC) {
          await wtAddStep(session, 'scroll_settle', { id: tabId || session.tabId });
        }
      }
      sendResponse({ ok: true });
    })();
    return true;
  });

  chrome.tabs.onUpdated.addListener(async (tabId, info) => {
    const session = await wtGetSession();
    if (!session || !session.active) return;
    if (session.tabId != null && tabId !== session.tabId) return;
    if (info.status === 'complete') {
      wtScheduleNavSnap(tabId);
    }
  });

  chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name !== 'pmwb-wt-keepalive') return;
    const session = await wtGetSession();
    if (session && session.active) {
      try {
        await chrome.alarms.create('pmwb-wt-keepalive', { delayInMinutes: 0.5 });
      } catch (e) { /* */ }
    }
  });

  if (chrome.action && chrome.action.onClicked) {
    chrome.action.onClicked.addListener(async (tab) => {
      const session = await wtGetSession();
      if (session && session.active) {
        await wtStop();
      } else {
        await wtStart(tab);
      }
    });
  }

  if (chrome.commands && chrome.commands.onCommand) {
    chrome.commands.onCommand.addListener(async (command) => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (command === 'pmwb-wt-mark') await wtMark(tab);
      if (command === 'pmwb-wt-stop') await wtStop();
      if (command === 'pmwb-wt-start') await wtStart(tab);
    });
  }
}

function wtAppendMenus() {
  chrome.contextMenus.create({
    id: 'pmwb-wt-sep',
    parentId: 'pmwb-root',
    type: 'separator',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'pmwb-wt-start',
    parentId: 'pmwb-root',
    title: 'Walkthrough: Start recording',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'pmwb-wt-mark',
    parentId: 'pmwb-root',
    title: 'Walkthrough: Mark step (screenshot now)',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'pmwb-wt-stop',
    parentId: 'pmwb-root',
    title: 'Walkthrough: Stop & save',
    contexts: ['page']
  });
}

async function wtHandleMenu(id, tab) {
  if (id === 'pmwb-wt-start') {
    await wtStart(tab);
    return true;
  }
  if (id === 'pmwb-wt-mark') {
    await wtMark(tab);
    return true;
  }
  if (id === 'pmwb-wt-stop') {
    await wtStop();
    return true;
  }
  return false;
}
