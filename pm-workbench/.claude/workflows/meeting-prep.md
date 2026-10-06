---
description: Before a meeting - assemble what you need in the time it takes to walk there
argument-hint: [who/what the meeting is about]
---

Meeting coming up about: $ARGUMENTS

Pull together, fast — this is meant to be ready before you sit down, not a research project:

1. **Check `registers/initiatives.csv`** for anything matching this topic — current stage, linked PRD/prototype/experiment.
2. **Check `registers/decisions.csv` and `risks.csv`** for anything relevant, especially anything unresolved or recently changed.
3. **Check `registers/commitments.csv`** for anything due from either side involving these stakeholders.
4. **Check recent `outputs/daily/*-meeting.md`** for the last time you met with these people on this topic — what was decided last time, what you told them would happen by now.
5. **Check open to-dos for this topic:** `python3 scripts/todo_register.py list --initiative "<topic>"` (skip if `registers/todos.csv` does not exist). Report open or overdue ones as a line under "Watch for" — a to-do is mine, not a promise to them, so keep it separate from commitments.
6. **Check `reference/links.csv`** for a relevant template, doc, or dashboard link worth having open.

Return one tight brief, not a report:
```
Going in, you should know:
- Last time: [what was decided/promised]
- Status since then: [what's actually happened]
- Open questions: [anything unresolved]
- Watch for: [a risk or a promise you made that hasn't landed yet]
```

If nothing's tracked on this topic yet, say so plainly — that's useful too (means you're not walking in missing context, there just isn't any yet).

**Cite inputs, not equivalence.** Naming `outputs/daily/…` as a source is fine. If a follow-up question re-reads the archive transcript and your reply is richer than that digest, say so (CLAUDE.md rule 23) — do not claim the digest "has it all."
