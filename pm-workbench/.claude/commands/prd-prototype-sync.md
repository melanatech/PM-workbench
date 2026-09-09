---
description: Check a PRD and its prototype against each other, anytime, without redoing either
argument-hint: [feature name]
---

Feature: $ARGUMENTS

Dispatch to `prd-prototype-reconciler` — it reconciles both `outputs/prds/[feature]/` and `prototypes/[feature]/` against the shared Feature Contract (`outputs/prds/[feature]/contract.md`), folding in `outputs/research/[feature]/` findings if they exist. Each divergence comes back as a choice (add to contract / label exploratory / remove), never an auto-fix.

Use this anytime something changes on either side outside the normal `/prd-package` or `/prototype-build` flow — a stakeholder comment that changed the PRD without a prototype update, or a build decision that changed the prototype without anyone updating the doc.
