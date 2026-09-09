---
description: Given something that just changed, trace what else in the system might need revisiting
argument-hint: [what happened - a decision, a Jira update, news, anything]
---

Something changed: $ARGUMENTS

This is for anything that happened outside the normal command flow — a hallway decision, a Slack thread, news that didn't go through `/meeting-closeout` or `/discovery`. Trace its implications the same way those commands would:

1. Check `registers/initiatives.csv` — does this touch anything at prd/prototype/experiment/launched stage? Name it and its current stage explicitly.
2. Check `registers/evidence.csv` — does this confirm, contradict, or add to existing evidence on this topic?
3. Check `registers/decisions.csv` and `registers/risks.csv` — does this conflict with a prior decision, or introduce a new risk?
4. Check `state/okr-history.csv` — does this affect a metric or target?

For each thing it touches, say plainly what command would normally handle formalizing it, and why:
```
Affects: [initiative/evidence/decision/metric]
Currently: [its current state]
This changes: [what specifically]
Suggested next step: run /prd-package | /jira-reconcile | /experiment-analyze | ... — or "just log it" if nothing downstream actually needs to move.
```

If it touches nothing tracked yet, say so — not everything needs to ripple, and a false "this affects everything" report is as useless as missing a real connection. Offer to log it as a new entry in the relevant register if it should exist somewhere but doesn't yet.
