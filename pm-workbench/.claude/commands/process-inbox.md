---
description: Process all new raw captures in inbox/ into structured records and registers
---

Work through every unprocessed file in `inbox/` (check `state/processed-files.txt` for what's already done).

For each file:
1. Identify what it is: discovery signal, meeting notes (including `[timestamp]-quick.md` drops from `/quick-close` — these get the FULL reconciliation treatment now that there's time), metric export, research notes, competitive capture, launch material, or **a document** (PDF/Word/PowerPoint/Excel in `inbox/documents/`) — route by content, not just folder.
2. **Privacy in durable records:** when writing evidence rows or research summaries, use concise summaries + source links, and redact customer names/identifiers (per CLAUDE.md rule 15) — the exact wording can stay brief and anonymized; the full raw text stays in archive/ as temporary working material, not in the permanent register.
3. **Documents:** if it's a binary format, try `scripts/extract_document.sh [file]`; if it's still a stub or fails, don't stall — try reading directly, use macOS `textutil` via bash for Word formats, or ask me to re-export/paste the text, and log the gap in BACKLOG.md. Then: if it's a user research report, create/update its summary in `reference/user-research/` per that folder's README, and pull any findings that update `registers/evidence.csv`. If it's something else (a strategy doc, a decision record), route it to wherever it's actually about — `learning/[area]/`, `registers/decisions.csv`, or flag it to me if it's unclear where it belongs.
4. **Discovery material** → one evidence record per distinct problem observation, appended to `registers/evidence.csv` using its exact schema. Preserve the customer/user's exact wording in `exact_observation`; your reading goes in `interpreted_problem`. Mark `evidence_type` honestly: direct / reported / inferred.
5. **Meeting notes** → route through the `/meeting-closeout` logic (decisions/commitments/risks to registers).
6. **Metric exports (CSV)** → leave in `inbox/metrics/` for `/okr-refresh`; just note them in the run report.
7. Deduplicate: before appending, check whether a materially similar evidence record (or research summary) already exists — if so, link (note the existing evidence_id or research file) rather than duplicate.
8. Move each processed file to `archive/` (never edit or delete originals) and append its name to `state/processed-files.txt`.

End with a quality-control report in chat: files processed, records created, duplicates linked, anything skipped and why, and anything that looked important but didn't fit a category.
