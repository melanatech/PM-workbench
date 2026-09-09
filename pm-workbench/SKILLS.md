# SKILLS.md — where commands become skills (and why you might care)

You asked about skills. Short version: **skills are the newer format of the exact same thing your commands already are**, with one meaningful upgrade.

A command is a markdown file at `.claude/commands/okr-refresh.md` → you type `/okr-refresh`.
A skill is the same content at `.claude/skills/okr-refresh/SKILL.md` → you can still type `/okr-refresh`, **and** Claude can now invoke it on its own when it recognizes the situation calls for it.

That auto-invocation is the practical difference. With commands, if you say "hey, pull this week's numbers," Claude improvises. With skills, it recognizes that's the okr-refresh job and runs your tuned, battle-tested version — same guardrails, same output format — without you remembering the exact command name. Skills can also bundle extra files (reference docs, scripts) in their folder that load only when the skill runs, which keeps sessions lean.

## Recommended path: don't convert yet
The kit ships as commands deliberately. Weeks 1-3 are for tuning prompts — editing one flat file per workflow is faster iteration. Convert a workflow to a skill when it's stable and you notice yourself describing the task in natural language instead of typing the slash command.

## Converting one (it's just a file move)
```
mkdir -p .claude/skills/okr-pull
mv .claude/commands/okr-refresh.md .claude/skills/okr-refresh/SKILL.md
```
Then add a `description:` line to the frontmatter if it doesn't have one — that's what Claude reads to decide when to auto-invoke. Make it describe the *situation* ("Pull current OKR metrics from dashboards and draft the weekly numbers update") rather than just naming the command.

## Best first candidates for conversion, once stable
- `discovery` and `okr-refresh` — the recurring ones you'll eventually stop thinking about
- `meeting-closeout` — because you'll paste notes and say "close this out" without remembering a command name
- `ripple-check` — "does this affect anything?" is exactly the phrasing skills auto-invoke on

One caution now that the kit has a command-menu table in CLAUDE.md: that table already gives you plain-language routing in interactive sessions, so the marginal benefit of converting is smaller than it once was. Convert only if you find the menu routing missing things.


## Already converted: prototype-build (and why it went first)
`prototype-build` is now a skill (`.claude/skills/prototype-build/SKILL.md`) rather
than a flat command — it's the first conversion because it needed to bundle files:
a real QA harness (`qa/qa-prototype.mjs` + `qa/README.md`) that only loads when the
skill runs. It also gained type-awareness (static / React-web / Expo-mobile), real
repo scaffolding for complex prototypes, company design-source import (component
library and/or style guide), and a **runtime QA step that actually renders and
clicks the prototype in a browser** before stakeholder review — closing the gap
where a prototype could look right in code but be visually broken. See its
`qa/README.md` for the browser prerequisites (Claude Code, not chat-only).
