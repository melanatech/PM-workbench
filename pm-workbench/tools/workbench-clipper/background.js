// PM Workbench Clipper — a human clicks, a file lands in Downloads/pm-workbench-inbox/.
// Then `python3 scripts/pull_clips.py` (or /process-inbox) moves it into inbox/captures/.
// Nothing here browses, clicks, or submits. It only reads what you are already looking at.

const CATEGORIES = [
  ['discovery',   'Discovery signal (customer / support / feedback)'],
  ['competitive', 'Competitive'],
  ['meetings',    'Meeting notes / summary'],
  ['metrics',     'Metric / dashboard reading'],
  ['documents',   'Internal document'],
  ['captures',    'Just capture it (classify later)']
];

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: 'pmwb-root', title: 'Send to PM Workbench', contexts: ['page', 'selection'] });
  for (const [id, title] of CATEGORIES) {
    chrome.contextMenus.create({ id: 'pmwb-' + id, parentId: 'pmwb-root', title, contexts: ['page', 'selection'] });
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!info.menuItemId.startsWith('pmwb-') || info.menuItemId === 'pmwb-root') return;
  const category = info.menuItemId.slice(5);
  let body = info.selectionText || '';
  if (!body && tab && tab.id) {
    try {
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => (document.querySelector('main, article') || document.body).innerText.slice(0, 60000)
      });
      body = result || '';
    } catch (e) { body = '(page text could not be read — paste it manually)'; }
  }
  const now = new Date();
  const stamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const slug = (tab && tab.title ? tab.title : 'capture').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
  const md = [
    '---',
    `captured: ${now.toISOString()}`,
    `category: ${category}`,
    `source_url: ${info.pageUrl || (tab && tab.url) || ''}`,
    `title: ${(tab && tab.title || '').replace(/\n/g, ' ')}`,
    `capture_kind: ${info.selectionText ? 'selection' : 'page'}`,
    'access_path: PM Workbench Clipper — read from the page the PM was viewing in a logged-in browser; not fetched by the model',
    '---',
    '',
    body
  ].join('\n');
  const url = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(md);
  chrome.downloads.download({ url, filename: `pm-workbench-inbox/${category}/${stamp}-${slug}.md`, saveAs: false, conflictAction: 'uniquify' });
});
