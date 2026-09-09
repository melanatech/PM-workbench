# Prototype QA harness

Real runtime QA — boots the prototype in a headless browser, walks its states,
clicks its controls, captures console errors and screenshots, writes
`qa-report.md`. This is a **visual/behavioral** check, not a logic check.

## Prerequisites (one time)
```
npm install -g playwright        # or: npm i -D playwright in the prototype
npx playwright install chromium  # downloads the browser binary
```
These need real network + local execution. That means **Claude Code on your
machine** — not the chat-only sandbox, which has no browser and blocks package
installs. If you're in chat-only mode, the skill runs structural checks and says
so; it does not fake a visual pass.

## Run it
```
# static (single HTML file)
node .claude/skills/prototype-build/qa/qa-prototype.mjs \
  --type static --path prototypes/manager-scorecards \
  --states "loaded,empty,error,denied,compare"

# web (React/Vite/etc.) — installs, builds, boots dev server, tests localhost
node .claude/skills/prototype-build/qa/qa-prototype.mjs \
  --type web --path prototypes/scorecards-app \
  --run "npm run dev" --url http://localhost:5173 \
  --states "loaded,empty,error,denied"

# mobile (Expo) — uses the Expo *web* render so no simulator is needed
node .claude/skills/prototype-build/qa/qa-prototype.mjs \
  --type mobile --path prototypes/scorecards-mobile \
  --states "loaded,empty,error,denied"
```

## How states are reached
The harness clicks a control matching each state name — either
`[data-state="empty"]` / `[data-st="empty"]`, or a button whose visible text
matches (e.g. an "Empty" toggle). **So build your prototype's state switcher with
`data-state` attributes** and the walk is automatic. If a state can't be reached,
the report flags it `reached: NO` rather than pretending.

## What a pass means (and doesn't)
- PASS = it booted, every declared state rendered, controls clicked without
  console errors, instrumentation labels were visible. A real render happened.
- It does **not** verify pixel-perfect design or business correctness — that's
  what the stakeholder reviewers and your own eyes on the screenshots are for.
- Native mobile beyond Expo-web (true simulator testing) is out of scope here;
  the skill falls back to a build check + a manual checklist, clearly labeled.
