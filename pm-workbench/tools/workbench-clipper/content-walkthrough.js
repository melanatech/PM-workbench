// Injected while a walkthrough session is active. Passive — does not click or submit.
(function () {
  if (window.__pmwbWalkthroughBound) return;
  window.__pmwbWalkthroughBound = true;

  const TEXT_MAX = 120;
  let scrollTimer = null;
  let lastReportedScrollY = window.scrollY || 0;

  function trunc(s) {
    return String(s || '').replace(/\s+/g, ' ').trim().slice(0, TEXT_MAX);
  }

  function shortPath(el) {
    if (!el || el.nodeType !== 1) return '';
    const parts = [];
    let cur = el;
    for (let i = 0; i < 4 && cur && cur.nodeType === 1; i++) {
      let bit = cur.tagName.toLowerCase();
      if (cur.id) {
        bit += '#' + cur.id.replace(/\s/g, '');
        parts.unshift(bit);
        break;
      }
      const cls = (cur.className && typeof cur.className === 'string')
        ? cur.className.trim().split(/\s+/).slice(0, 2).join('.')
        : '';
      if (cls) bit += '.' + cls;
      parts.unshift(bit);
      cur = cur.parentElement;
    }
    return parts.join(' > ').slice(0, 200);
  }

  function send(payload) {
    try {
      chrome.runtime.sendMessage(Object.assign({ source: 'pmwb-walkthrough' }, payload));
    } catch (e) {
      /* extension context invalidated */
    }
  }

  document.addEventListener('click', (ev) => {
    const el = ev.target && ev.target.closest ? ev.target.closest('a,button,[role="button"],input,select,summary,[onclick]') || ev.target : ev.target;
    if (!el || el.nodeType !== 1) return;
    const tag = el.tagName.toLowerCase();
    send({
      type: 'click',
      ts: new Date().toISOString(),
      url: location.href,
      title: document.title,
      tag,
      text: trunc(el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.value || ''),
      href: tag === 'a' ? (el.href || '') : '',
      path: shortPath(el),
      scrollY: Math.round(window.scrollY || 0)
    });
  }, true);

  document.addEventListener('focusout', (ev) => {
    const el = ev.target;
    if (!el || !el.tagName) return;
    const tag = el.tagName.toLowerCase();
    if (tag !== 'input' && tag !== 'textarea' && tag !== 'select') return;
    const inputType = (el.type || tag).toLowerCase();
    if (inputType === 'password') {
      send({
        type: 'input',
        ts: new Date().toISOString(),
        url: location.href,
        title: document.title,
        field: trunc(el.name || el.id || el.getAttribute('aria-label') || 'password'),
        inputType: 'password',
        redacted: true
      });
      return;
    }
    send({
      type: 'input',
      ts: new Date().toISOString(),
      url: location.href,
      title: document.title,
      field: trunc(el.name || el.id || el.getAttribute('aria-label') || el.placeholder || tag),
      inputType,
      redacted: false,
      valueLen: (el.value || '').length
    });
  }, true);

  window.addEventListener('scroll', () => {
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      const y = Math.round(window.scrollY || 0);
      const vh = Math.round(window.innerHeight || 0);
      send({
        type: 'scroll',
        ts: new Date().toISOString(),
        url: location.href,
        title: document.title,
        scrollY: y,
        viewportH: vh,
        deltaFromLast: Math.abs(y - lastReportedScrollY)
      });
      lastReportedScrollY = y;
    }, 500);
  }, { passive: true });

  // SPA / pushState URL changes
  const pushState = history.pushState;
  history.pushState = function () {
    pushState.apply(this, arguments);
    setTimeout(() => {
      send({
        type: 'url',
        ts: new Date().toISOString(),
        url: location.href,
        title: document.title,
        scrollY: Math.round(window.scrollY || 0)
      });
    }, 0);
  };
  window.addEventListener('popstate', () => {
    send({
      type: 'url',
      ts: new Date().toISOString(),
      url: location.href,
      title: document.title,
      scrollY: Math.round(window.scrollY || 0)
    });
  });

  send({
    type: 'ready',
    ts: new Date().toISOString(),
    url: location.href,
    title: document.title,
    scrollY: Math.round(window.scrollY || 0)
  });
})();
