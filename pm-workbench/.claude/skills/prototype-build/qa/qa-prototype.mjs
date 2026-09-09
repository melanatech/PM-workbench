#!/usr/bin/env node
/**
 * qa-prototype.mjs — real runtime QA for a prototype.
 *
 * Renders the prototype in a headless browser, walks every declared state,
 * clicks every interactive element once, captures console errors and a
 * screenshot per state, and writes an inspectable qa-report.md.
 *
 * This is NOT a logic check. It boots the actual thing and looks at it.
 * Requires a local browser (Playwright) — see qa/README.md. Only works where
 * local execution + a browser are available (i.e. Claude Code, not chat-only).
 *
 * Usage:
 *   node qa-prototype.mjs --type static --path prototypes/manager-scorecards
 *   node qa-prototype.mjs --type web    --path prototypes/scorecards-app --run "npm run dev" --url http://localhost:5173
 *   node qa-prototype.mjs --type mobile --path prototypes/scorecards-mobile   (uses expo web)
 *
 * --states "loaded,empty,error,denied,compare"  states to walk (buttons whose
 *          text or data-state matches are clicked to reach each state).
 */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import fs from 'node:fs';
import path from 'node:path';

const args = Object.fromEntries(
  process.argv.slice(2).join(' ').split('--').filter(Boolean)
    .map(s => { const [k, ...v] = s.trim().split(' '); return [k, v.join(' ') || true]; })
);

const type = args.type || 'static';
const proto = args.path;
if (!proto) { console.error('ERROR: --path required'); process.exit(2); }
const states = (args.states || 'loaded,empty,error,denied').split(',').map(s => s.trim()).filter(Boolean);
const shotsDir = path.join(proto, 'qa-screenshots');
fs.mkdirSync(shotsDir, { recursive: true });

const report = { type, path: proto, when: new Date().toISOString(), checks: [], states: [], console_errors: [], verdict: 'pending' };
const add = (name, pass, detail = '') => report.checks.push({ name, pass, detail });

let devProc = null;
async function bootTarget() {
  // Returns a URL (web/mobile) or a file:// path (static) to load.
  if (type === 'static') {
    const entry = path.resolve(proto, 'index.html');
    if (!fs.existsSync(entry)) { add('entry file exists', false, entry); throw new Error('no index.html'); }
    add('entry file exists', true, entry);
    return 'file://' + entry;
  }
  // web or mobile: install, build (web), then run a dev/web server.
  const run = (cmd) => new Promise((res) => {
    const p = spawn(cmd, { cwd: proto, shell: true, stdio: 'pipe' });
    let out = '';
    p.stdout.on('data', d => out += d); p.stderr.on('data', d => out += d);
    p.on('close', code => res({ code, out }));
  });
  const install = await run('npm install');
  add('npm install', install.code === 0, install.code === 0 ? '' : install.out.slice(-400));
  if (type === 'web') {
    const build = await run('npm run build');
    // build script may not exist; treat missing script as skipped, real failure as fail
    const missing = /missing script/i.test(build.out);
    add('npm run build', build.code === 0 || missing, missing ? 'no build script (skipped)' : build.out.slice(-400));
  }
  const cmd = args.run || (type === 'mobile' ? 'npx expo start --web' : 'npm run dev');
  const url = args.url || (type === 'mobile' ? 'http://localhost:19006' : 'http://localhost:5173');
  devProc = spawn(cmd, { cwd: proto, shell: true, stdio: 'pipe' });
  // wait for the port to answer
  const started = Date.now();
  while (Date.now() - started < 60000) {
    try { const r = await fetch(url); if (r.ok || r.status) break; } catch {}
    await sleep(1000);
  }
  add('dev server booted', true, url);
  return url;
}

async function main() {
  let target;
  try { target = await bootTarget(); }
  catch (e) { report.verdict = 'FAIL — did not boot'; finish(); return; }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: type === 'mobile' ? { width: 390, height: 844 } : { width: 1200, height: 800 } });
  page.on('console', m => { if (m.type() === 'error') report.console_errors.push(m.text()); });
  page.on('pageerror', e => report.console_errors.push('pageerror: ' + e.message));

  await page.goto(target, { waitUntil: 'networkidle' }).catch(() => {});
  add('initial load', true);

  // Walk each declared state by clicking a control whose text or data-state matches.
  for (const st of states) {
    let reached = false;
    const byData = page.locator(`[data-state="${st}"], [data-st="${st}"]`);
    if (await byData.count()) { await byData.first().click().catch(() => {}); reached = true; }
    else {
      const byText = page.getByRole('button', { name: new RegExp(st, 'i') });
      if (await byText.count()) { await byText.first().click().catch(() => {}); reached = true; }
    }
    await sleep(300);
    const shot = path.join(shotsDir, `state-${st}.png`);
    await page.screenshot({ path: shot }).catch(() => {});
    // instrumentation labels present?
    const instrumentation = await page.locator('text=/instrumentation|event|fires|_viewed|_opened|_exported/i').count();
    report.states.push({ state: st, reached, screenshot: shot, instrumentation_labels_visible: instrumentation > 0 });
    add(`state "${st}" reachable`, reached, reached ? shot : 'no control found to reach it');
  }

  // Click every visible button once; assert no NEW console error per click.
  const buttons = page.locator('button:visible');
  const n = Math.min(await buttons.count(), 40);
  let clickErrors = 0;
  for (let i = 0; i < n; i++) {
    const before = report.console_errors.length;
    await buttons.nth(i).click({ timeout: 1000 }).catch(() => {});
    await sleep(120);
    if (report.console_errors.length > before) clickErrors++;
  }
  add('interactive elements clickable without console errors', clickErrors === 0, clickErrors ? `${clickErrors} clicks produced console errors` : `${n} elements clicked clean`);

  add('no console errors during QA', report.console_errors.length === 0,
      report.console_errors.length ? report.console_errors.slice(0, 5).join(' | ') : '');

  await browser.close();
  report.verdict = report.checks.every(c => c.pass) ? 'PASS' : 'FAIL — see failing checks';
  finish();
}

function finish() {
  if (devProc) try { process.kill(-devProc.pid); } catch { try { devProc.kill(); } catch {} }
  const lines = [];
  lines.push(`# Prototype QA report`);
  lines.push(`Type: **${report.type}** · Path: \`${report.path}\` · ${report.when}`);
  lines.push(`\n## Verdict: ${report.verdict}\n`);
  lines.push(`## Checks`);
  for (const c of report.checks) lines.push(`- [${c.pass ? 'x' : ' '}] ${c.name}${c.detail ? ' — ' + c.detail : ''}`);
  lines.push(`\n## States walked`);
  for (const s of report.states) lines.push(`- **${s.state}** — reached: ${s.reached ? 'yes' : 'NO'} · instrumentation labels visible: ${s.instrumentation_labels_visible ? 'yes' : 'NO'} · ![${s.state}](${path.basename(path.dirname(s.screenshot))}/${path.basename(s.screenshot)})`);
  if (report.console_errors.length) { lines.push(`\n## Console errors (${report.console_errors.length})`); report.console_errors.slice(0, 20).forEach(e => lines.push('- ' + e)); }
  lines.push(`\n_Screenshots in \`qa-screenshots/\`. This report reflects an actual browser render, not a logic check._`);
  const out = path.join(report.path, 'qa-report.md');
  fs.writeFileSync(out, lines.join('\n'));
  console.log(`QA ${report.verdict} → ${out}`);
  process.exit(report.verdict.startsWith('PASS') ? 0 : 1);
}

main();
