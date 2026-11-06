status: template
last_updated:

# PM brain

Working memory. `CLAUDE.md` imports this file with `@reference/context/pm-brain.md`, so
Claude Code reloads it at session start and after `/compact` — the facts here survive a
resume without anyone repeating them.

**How it gets written.** One scenario: you state or correct a standing fact in chat (a
belief, preference, date, scope, owner, priority, roadmap rule, or taste note) so the next
session does not re-ask or undo it. Claude writes that back here and updates every
current-state register row that still states the old fact, in the same turn (Tier 1, no
approval). One line: "Updated RISK-010, COM-010: …".
At session start, partner mode and `/brief daily-brief` reread your turns for standing
facts that are missing. They do not copy an answer or an investigation into this file.

**Not this scenario.** Claude answering a question, confirming bugs, or closing an
investigation. That answer stays in the deliverable (`outputs/`, `drafts/`, todo proposals,
`learning/`, or a register). Agreeing the answer was right does not make it a brain line.

**How it stays short.** Keep it under 600 words. Past that, the next session start condenses
it: merge duplicates, move backlog dumps out, and mark a line that a newer one supersedes
as `(replaced <date>)` rather than keeping both.

**It is yours.** Edit or delete any line freely — this is working memory, not a register.
Current-state register rows that still state the old fact are updated in that same turn.
History rows are not rewritten.

Copy to `reference/context/pm-brain.md` (a new live workspace does this). Remove
`status: template` and set `last_updated` once it holds real lines.

---

## Current beliefs and bets

What you think is true about the market, the users, and where this product should go.
One dated line each. A belief you have changed gets the new line plus `(replaced <date>)`
on the old one.

-

## Settled product facts

Things that are decided and should never be re-litigated or re-asked: what has shipped,
what the chosen surface is, what is in scope for you to touch, what the naming is.

-

## Roadmap rules

How you want a roadmap expressed: deliverable names rather than themes, the time
granularity, the column scheme and how items are ordered inside a column, and which
items are yours to move.

-

## Taste notes

What you praised and what you rejected, quoted briefly, with the date. This is what a
draft gets measured against before you see it. Not a session log and not a ticket backlog.

-
