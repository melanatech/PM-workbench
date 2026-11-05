// Pure decisions for Stream transcript scrolling.
// Loaded into the page before extractPagePayload. A virtualized list
// reports a scroll height that is shorter than the transcript, so a
// clamped scrollTop is not the end.

(function (root) {
  function formatMissing(missing) {
    if (!missing || !missing.length) return '';
    const parts = [];
    let start = missing[0];
    let prev = missing[0];
    for (let i = 1; i < missing.length; i += 1) {
      const n = missing[i];
      if (n === prev + 1) {
        prev = n;
        continue;
      }
      parts.push(start === prev ? String(start) : start + '-' + prev);
      start = n;
      prev = n;
    }
    parts.push(start === prev ? String(start) : start + '-' + prev);
    return parts.join(',');
  }

  function scrollTopForPos(scrollHeight, clientHeight, pos, setSize) {
    const maxTop = Math.max(0, scrollHeight - clientHeight);
    const size = setSize > 1 ? setSize : 2;
    const ratio = Math.min(1, Math.max(0, (pos - 1) / (size - 1)));
    return Math.round(ratio * maxTop);
  }

  // Give up only after repeated probes that grow neither the collected
  // rows nor the scroll height. Being at the reported bottom does not
  // count as done while rows are still missing.
  function noteProbe(dead, probe) {
    const grew = !!(probe && (probe.countGrew || probe.heightGrew));
    if (grew) return { dead: 0, giveUp: false };
    const next = (dead || 0) + 1;
    return { dead: next, giveUp: next >= 8 };
  }

  const api = {
    formatMissing: formatMissing,
    scrollTopForPos: scrollTopForPos,
    noteProbe: noteProbe,
    giveUpAfter: 8
  };
  root.pmwbScrollPolicy = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
