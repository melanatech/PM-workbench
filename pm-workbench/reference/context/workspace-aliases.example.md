# Workspace aliases (name → path)

When the PM (or a capture) names a surface — "events digest", "weekly scorecard" — **look it up here first**, then search (`context_preflight` / Glob), then ask. Do **not** guess the nearest-sounding file (for example `glossary.md` for a metric workbook).

Copy this file into your live workspace as `reference/context/workspace-aliases.md` and keep it updated. Put company-specific names (report areas, metric workbooks, internal digests) in the live copy only.

Publishing does not ban every alias. `external_treatment` says what an outside reader should see. The test is whether that reader understands the phrase, and whether the phrase is confidential — not whether the workbench or the company coined it.

| Treatment | What publishing does | `external_value` |
|---|---|---|
| `internal_only` | Block when the phrase appears | leave empty |
| `expand` | Replace the phrase with a spelling an outside reader understands | the spelled-out phrase |
| `preserve` | Leave the phrase | leave empty |
| `neutralize` | Replace a workspace path or process label with a neutral description | that description |
| empty, or anything else | Block and ask for one of the four treatments. This is the safe default, including a row that still has only Phrase, Path, and Meaning | leave empty |

| Phrase | Path | Meaning | external_treatment | external_value |
|---|---|---|---|---|
| events digest / instrumentation digests | `outputs/daily/*events*` | Prior analysis of analytics events — authority before re-reading `repos/` | neutralize | prior analysis of analytics events |
| weekly scorecard | `outputs/weekly/` | Leadership update drafts | expand | weekly leadership update |
| glossary | `reference/context/glossary.md` | Standing acronyms for chat — not metric-field definitions | preserve | |
| schema codename | `outputs/weekly/` | Schema example only: a confidential nickname. Delete this row if you do not use it. | internal_only | |
| unclassified label | `outputs/weekly/` | Schema example only: left unclassified on purpose so publishing blocks until you set external_treatment. Delete this row if you do not use it. | | |

_Add a row when a name you use often maps to a specific path. Leave `external_treatment` empty until you know how an outside reader should meet that name._
