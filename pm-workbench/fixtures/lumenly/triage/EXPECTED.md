# Source-triage expected outcomes (Lumenly)

Manual / agent check for `_source-triage.md`. Not scored by `score_fixture.py`.

| File | Role | Outcome | Notes |
|---|---|---|---|
| `documents/2027-okr-frame.html` | strategy | promote | `strategy-frame`; surface 5 proposal-only |
| `documents/glossary-mapu.txt` | semantic-system | promote | acronym → `term` → glossary |
| `documents/definitions-frag-1.md` | semantic-system | hold | fragment; wait for siblings |
| `documents/definitions-frag-2.md` | semantic-system | hold → promote on match | second primary confirms |
| `documents/definitions-frag-3.md` | semantic-system | hold → promote on match | third; raise INITIATIVE CANDIDATE (≥3 criteria) |
| `documents/ssl-rotation-note.md` | engineering | ignore | routine infra; keep-list miss |
| `meetings/2026-10-15-things-to-think-about.md` | exploratory-thinking | hold | no EV/DEC/COM; no owner questions |
| `documents/okr-frame.png` | strategy | duplicate | same content as html; `same_as` = html |
| `meetings/2026-10-15-short.txt` | exploratory-thinking | duplicate | shorter transcript; `same_as` = full |
| `drafts/returned-brief.md` | other | index | origin `derived-own`; never evidence |
| `exports/ai-digest.md` | operating-update | hold | origin `ai-summary`; cannot confirm alone |
| `exports/status-done.txt` | operating-update | promote | claim tagged `needs-authority` |
| `exports/partner-payouts.csv` | data | index | profile redacted; sensitivity=commercial |

Run after wiring: load these into an isolated inbox and `/capture process-inbox`.
