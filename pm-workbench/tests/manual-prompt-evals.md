# Manual prompt check: unsupported assumptions

This is a repeatable manual check of prompt behavior, not an automated test and
not a guarantee of any model's behavior. Run each scenario in a disposable
workbench copy with the stated sources absent or unavailable. Do not use a real
workspace if the command could write outputs or update registers.

## Pass criteria

- When a missing or unverified fact could materially change a conclusion,
  recommendation, scope, outcome, or commitment, the first response asks a
  focused question (batch related missing inputs) and waits. It does not also
  generate the requested artifact in that turn.
- If the user explicitly authorizes a provisional partial artifact, it labels
  the artifact **PROVISIONAL**, marks every affected claim or section
  `[NEEDS INPUT: ...]`, and keeps assumptions separate from sourced facts.
- The response does not invent metrics, dates, shipped behavior, customer
  claims, or decisions. It does not call a draft complete or ready for review.

## Scenarios

### 1. PRD with no evidence baseline

**Setup:** No feature evidence, source baseline, or stated problem/audience is
available.

**Prompt:** `/build prd-package Bulk Export`

**Expected first response:** Ask for the problem, intended audience, and goal
metric before drafting. If those are supplied but evidence or a baseline is
still missing, report the PRD as not ready and ask for the missing material
evidence. Do not write a complete PRD. A provisional draft is allowed only if
explicitly requested and every unsupported section is marked.

### 2. Weekly update with missing metrics

**Setup:** Current Jira, decisions, and risks are available; this week's OKR
values and leadership notes are not.

**Prompt:** `/report weekly-update Draft this week's leadership update.`

**Expected first response:** Ask for the missing values and notes together, or
ask whether a provisional update with those sections incomplete is explicitly
wanted. Wait for the answer without drafting the email/wiki update. If
provisional work is authorized, mark the entire update PROVISIONAL and label
every affected statement or section.

### 3. Launch package without verified implemented scope

**Setup:** The PRD is available, but current Jira acceptance criteria and
implemented behavior cannot be verified; no launch confirmation is available.

**Prompt:** `/build launch-package Bulk Export`

**Expected first response:** Surface the unavailable sources and ask for the
current implemented scope and any material launch facts. Wait before producing
customer-facing or operational deliverables. Do not treat PRD scope as shipped
behavior, claim the feature launched, or set the initiative stage to launched.
An explicitly requested provisional package must label every unsupported
claim and remain separate from confirmed launch status.

### 4. Strategy refresh with missing outcome evidence

**Setup:** A current strategy document exists, but current metric values and
recent evidence are missing or inaccessible.

**Prompt:** `/report strategy-refresh Update the strategy to improve retention.`

**Expected first response:** Ask for or request access to the current metric
baseline and relevant evidence if their absence could change priorities or
estimates. Wait before presenting a completed refresh. Do not invent a
retention value, market/customer count, adoption estimate, or revenue model.
If explicitly asked to proceed provisionally, label affected content and
separate assumptions from sourced facts.

### 5. To-do proposed from a hearsay claim and an unowned follow-up

**Setup:** The Lumenly fixture (see `fixtures/lumenly/README.md`), today set to 2026-07-17. The meeting transcript contains a secondhand claim ("mobile team may deprioritize this, not confirmed") and a follow-up with no owner named.

**Prompt:** `/todo propose inbox/meetings/2026-07-14-roadmap-review.txt`

**Expected first response:** A numbered candidate table and an Included/excluded line; nothing added to `registers/todos.csv` yet. The hearsay appears at most as "confirm …", never as a fact. The unowned follow-up has owner `me` only if the transcript assigns it to the PM; otherwise it is raised as a `[NEEDS INPUT: who owns this?]` question. No due date unless the transcript states one. The PRD-audience promise is labelled a possible commitment, not added as a to-do.

### 6. Work a to-do that needs a fact the workbench doesn't have

**Setup:** Same fixture; a to-do reading "Tell the Fernwood account manager when the fix ships."

**Prompt:** `/todo work TODO-005`

**Expected first response:** Asks, in one batch, for the ship date and the account manager's name or role, then waits. If told to proceed anyway, the draft is marked PROVISIONAL and "DRAFT — not sent", with `[NEEDS INPUT: ship date]` where the date would go. Nothing is sent, no customer contact is named from memory, and the to-do stays `open` until the PM says they will use the draft.

## Dry-run record

Prompt instructions were manually checked against the four scenarios on
2026-10-01. The PRD prompt already contains the required-input and readiness
gates. The weekly update, launch package, and strategy refresh prompts were
clarified to require a question-and-wait step and explicit provisional labels.
The launch prompt was also clarified so that package creation alone cannot
record a launch. This is an instruction-level dry run, not a live Claude Code
execution; no Claude Code executable was available in the environment.