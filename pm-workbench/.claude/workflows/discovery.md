---
description: Your discovery workbench - ask what the evidence says, add new inputs, see what changed, or map the opportunity space
argument-hint: [a question, notes to add, "what's new", or "map opportunities"]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Request: $ARGUMENTS

This is a continuous-discovery tool, not a one-shot report. Discovery is the ongoing work of deciding what to build, grounded in evidence — so this command has four modes, inferred from what I ask (or I can say which):

**1. Answer a question from the whole evidence base.** "What do we know about export reliability?" / "Is there evidence managers want per-location views?" — search ALL of `registers/evidence.csv`, `reference/user-research/`, past interview notes, and support/discovery captures, not just recent files. Answer with the evidence, each point sourced and dated, distinguishing direct customer evidence from stakeholder opinion, and volume from strength (three mentions of one theme from one account is not three independent signals). If the evidence is thin or one-sided, say so — that gap is itself a finding.

**2. Ingest new input.** Paste an interview transcript, a support thread, field notes, a survey export, or point at a file. I extract distinct observations into `registers/evidence.csv` (exact wording preserved separately from interpretation), tag them, and flag any that confirm or contradict an existing belief. Per continuous-discovery practice, single-interview synthesis comes first ("what did this one person say"), kept distinct from cross-interview synthesis, so minority signals aren't averaged away.

**3. Surface what changed.** "What's new since last week?" — scan inputs newer than the last review and report the delta: new themes, themes gaining or losing evidence, and newly contradicted assumptions. This is one mode, not the whole command.

**4. Map the opportunity space.** "Map opportunities around the Monday review" — cluster evidence into an opportunity structure (the customer needs/pain points/desires under a target outcome), showing which are well-evidenced vs. thin, and where an opportunity has no solution in flight (or a solution has no opportunity behind it). Never invent opportunities the evidence doesn't support.

Across every mode: cross-check against `registers/initiatives.csv` and name when a finding touches something already being built. Name your sources and access paths. Recommend a next step only when the evidence warrants one — sometimes the honest output is "we don't know enough yet; here's the question to go answer."


## Relationship durability & known biases

- **Suggested links stay suggestions.** When I connect an observation to a theme,
  a feature, or another piece of evidence, that link is tagged `proposed` until
  you review it. Only `confirmed` links are treated as fact by other workflows.
  This prevents a guessed connection from silently hardening into the record.
- **Evidence decays.** A complaint from 8 months ago weighs less than the same
  complaint last week; I surface age and don't treat old evidence as current.
- **Volume ≠ strength.** Ten messages in one internal Slack thread is one loud
  channel, not ten signals. Internal discussion is weighted below direct customer
  evidence, and stakeholder retelling ("a customer told me…") is tagged as
  secondhand, distinct from the customer's own words.
- **Watch for:** duplicate observations, alias drift (same customer/feature under
  two names), missed evidence, segment bias, and conflicts between what people say
  and what behavior data shows — I flag these rather than smoothing them over.
