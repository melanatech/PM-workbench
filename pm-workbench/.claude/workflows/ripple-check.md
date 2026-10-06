---
description: Given something that just changed, trace what else in the system might need revisiting
argument-hint: [what happened - a decision, a Jira update, news, anything]
---

Something changed: $ARGUMENTS

This is for anything that happened outside the normal command flow — a hallway decision, a Slack thread, news that didn't go through `/capture meeting-closeout` or `/discover discovery`. Trace its implications the same way those commands would, then **apply the Tier 1 fan-out** (do not stop at a report).

1. Check `registers/initiatives.csv` — does this touch anything at prd/prototype/experiment/launched stage? Name it and its current stage explicitly.
2. Check `registers/evidence.csv` — does this confirm, contradict, or add to existing evidence on this topic?
3. Check `registers/decisions.csv` and `registers/risks.csv` — does this conflict with a prior decision, or introduce a new risk?
4. Check `state/okr-history.csv` — does this affect a metric or target?
5. Read and apply `.claude/workflows/_fan-out.md` — update every durable surface that applies (assumptions, learning, priorities, competitive, INIT notes, todo-proposals). Tier 3 changes still need explicit approval.

For each thing it touches, say plainly what command would normally handle formalizing the *next* heavy step, and why:
```
Affects: [initiative/evidence/decision/metric]
Currently: [its current state]
This changes: [what specifically]
Written now: [paths / row ids]   ← Tier 1 fan-out already done
Suggested next step: run /build prd-package | /sync jira-reconcile | /build experiment-analyze | ... — or "none — logged" if nothing downstream needs a workflow.
```

If it touches nothing tracked yet, say so — not everything needs to ripple, and a false "this affects everything" report is as useless as missing a real connection. Offer to create the missing INIT-/EV-/DEC- row if it should exist, then fan-out.

End with the Surfaces updated / N/A / Cross-initiative block from `_fan-out.md`.
