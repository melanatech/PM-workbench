---
description: Pull Downloads clips into inbox/, then process all waiting captures into registers
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Step 0 — intake gate (required; never skip; never claim empty without this output).**  
Clips land in `~/Downloads/pm-workbench-inbox/<category>/` first (Chrome limitation). Users will say "process clips / documents / upload" while files are still there — **Downloads is part of intake**, not optional.

From the live workspace (`~/pm-live` as first folder), run and **paste the full stdout** into the RESULT:

```bash
python3 scripts/intake_status.py --root "$(pwd)"
```

(If cwd is wrong, use `--root "$HOME/pm-live"`.) That script pulls every file from Downloads into `inbox/`, then lists `inbox_unprocessed=…`. 

Hard rules:
- If stdout says `STATUS: work waiting` → process every `inbox:` path listed. **Forbidden:** "inbox empty" / "nothing found."
- If `downloads_still_pending` > 0 after pull → say pull failed; retry or report PermissionError; do not proceed as empty.
- If `STATUS: nothing waiting` → only then say there is nothing to process.
- If the script exits 2 (bad live-root / blocked) → print the error; tell me to run `echo "$HOME/pm-live" > ~/.pm-workbench/live-root` if the marker points at a `/var/folders` or `/tmp` fixture path.

Do **not** substitute a bare `ls inbox/` for Step 0.

Each clip’s frontmatter (when `.md`) carries `source_url` and `access_path` — cite them. If `capture_kind: selection`, treat the body as a partial transcript and say so. For `.csv`/`.pdf`/office docs in `inbox/documents/` or `inbox/exports/`, treat as documents (step 3).

Work through every unprocessed file listed by intake_status (and any still in `inbox/` not in `state/processed-files.txt`).

For each file:
1. Identify what it is: discovery signal, meeting notes (including `[timestamp]-quick.md` drops from `/quick-close` — these get the FULL reconciliation treatment now that there's time), metric export, research notes, competitive capture, launch material, or **a document** (PDF/Word/PowerPoint/Excel in `inbox/documents/`) — route by content, not just folder.
2. **Privacy in durable records:** when writing evidence rows or research summaries, use concise summaries + source links, and redact customer names/identifiers (per CLAUDE.md rule 15) — the exact wording can stay brief and anonymized; the full raw text stays in archive/ as temporary working material, not in the permanent register.
3. **Documents:** run `bash scripts/extract_document.sh [file]` first (writes a sibling `.extracted.txt`). Use that text as the baseline.
   - Exit **0** → read the printed path; do not invent another extractor.
   - Exit **2** (unsupported, e.g. pptx/xlsx) or **3** (empty/encrypted/tool fail) → **one** recovery attempt only if cheap and known (e.g. file is already `.txt` readable, or I already exported a twin). Otherwise **stop that file**, ask me to re-export/paste, and continue the rest of the inbox. Log the gap once in BACKLOG.md if it's a new format gap.
   - One-off scripts are allowed only when the kit extractor is missing a format you can fix in <2 minutes **and** you will either succeed or fail once with a clear ask — no retry loops of invented Python/Swift.
   - **Vision pass (required for PDFs and for clipper PNGs):** charts, tables-as-images, and diagrams are not in the text extract — do not treat text-only as complete when the file is a PDF (or a clip with a sibling `.png`).
     1. For each `.pdf`: run `bash scripts/rasterize_pdf.sh [file]` (optional 2nd arg = max pages; default 40). It writes `<stem>.pages/page-NN.png` + `manifest.txt`. Keep that folder with the PDF when archiving.
     2. **Read the PNGs with the Read tool** (Claude vision). Default: every page up to **20**; if the PDF has more, say which pages stay on disk unread and offer to widen. Prefer vision for metric callouts, chart axes/labels, and slide tables; merge with `.extracted.txt` (text wins for prose; vision wins for numbers that only appear in images).
     3. Write a sibling `<stem>.vision.md` with: source path, as-of dates seen, metrics/tables transcribed, diagrams summarized, pages unread if any. Cite `page-NN.png` for claims that came from an image. Route from **text + vision** together into learning / evidence / okr-history / fan-out.
     4. For clipper captures: if frontmatter has `includes_images: viewport_png` (or a same-stem `.png` sits beside the `.md`), Read that PNG the same way and fold visuals into the capture summary — do not ignore the screenshot.
   Then: if it's a user research report, create/update its summary in `reference/user-research/` per that folder's README, and pull any findings that update `registers/evidence.csv`. If it's something else (a strategy doc, a decision record), route it to wherever it's actually about — `learning/[area]/`, `registers/decisions.csv`, or flag it to me if it's unclear where it belongs. **Long strategy/deck packs:** if the text+vision material is too large to hold cleanly in this Fast pass, dispatch `internal-docs-reader` for that file (and its `.vision.md` if present), then fan out from the brief — do not skim for "context constraints" (CLAUDE.md).
4. **Discovery material** → one evidence record per distinct item, appended to `registers/evidence.csv` using its exact schema. That includes **stakeholder-proposed enhancements and solution ideas** (table resize, lock a column, reuse components, in-product guidance) — do **not** skip them because they are not customer quotes. Preserve exact wording in `exact_observation`; your reading goes in `interpreted_problem`. Mark `evidence_type` honestly: **direct** (you heard/saw the user), **reported** (someone relays user feedback), **inferred** (a proposed fix or improvement with no attached observation). Inferred rows stay `confidence=low`. SOURCE-POLICY still holds: inferred/stakeholder ideas are input in the register, not proof of a customer problem — later synthesis must not treat them as equivalent to direct/reported.
5. **Meeting notes** → route through the `/capture meeting-closeout` logic (decisions/commitments/risks **and initiative seeding** to registers), including that workflow's **PM-scope filter**: do not invent COM-/INIT- rows for eng-only ops (SSL rotation, infra chores, etc.).
6. **Initiatives from non-meeting discovery** → after writing evidence, ensure each item has a home in `registers/initiatives.csv`: match `related_feature` / theme to an existing INIT- row and append the new `EV-nnn` plus a one-line enhancement note into that row's `notes` (update `last_updated`). If the capture names a PM-scoped product initiative that has no row yet, create one (`discovery` or `building` / `iterating` as fits; see meeting-closeout seeding rules). Do **not** create a new INIT- per small enhancement — fold into the parent initiative's notes. Never seed eng-only infra.
7. **Metrics (CSV exports *and* dated figures inside decks/docs)** → append verified rows to `state/okr-history.csv` (`metric,value,as_of_date,retrieved_date,source`) when the source names a metric and an as-of/report date — do not wait for a dashboard-only path (CLAUDE.md rule 5 / SOURCE-POLICY). Prefer newer `as_of_date` for the same definition; if definitions differ (e.g. one KR vs split cohorts), log distinct metric names and put the "which is official?" question in `reference/context/assumptions-and-open-questions.md`. Leave raw CSVs in `inbox/metrics/` noted for `/report okr-refresh` narration if a fuller report is still needed; still log the numbers here so history is not empty.
8. Deduplicate: before appending, check whether a materially similar evidence record (or research summary) already exists — if so, link (note the existing evidence_id or research file) rather than duplicate.
9. Move each processed file to `archive/` (never edit or delete originals) and append its name to `state/processed-files.txt`.

If any processed file contained follow-ups for me (or discovery that implies my next action): append candidates to `outputs/todo-proposals/[date]-proposals.md` the same way meeting-closeout does (`QUEUED — nothing added`). Also fold new assumptions/open questions into `reference/context/assumptions-and-open-questions.md` and durable product facts into `learning/[area].md` when present. Do not add to-dos to `registers/todos.csv` from here.

**Fan-out (required).** Read and apply `.claude/workflows/_fan-out.md` for the batch. Competitive clips or research that name vendors → `state/competitive/` and/or `outputs/monthly/competitive-log.md` in this run, not "file under competitive later." Cross-cutting themes → every relevant INIT- notes row + assumptions/priorities/learning as they apply.

End with a quality-control report in chat: files processed, records created (including INIT- seeded/updated), duplicates linked, anything skipped and why, anything that looked important but didn't fit a category, **and** the Surfaces updated / N/A / Cross-initiative block from `_fan-out.md`.

