# Fixture: sample postmortem

A fictional example of the postmortem the workbench-health workflow writes on its own (`.claude/workflows/workbench-health.md`, Postmortem). When the health read or the usage story shows a failed job, the same pass writes `outputs/monthly/[date]-[slug]-postmortem.md` from that job's transcripts, correction themes, and artifacts. The PM does not draft it. In a quiet month there is no postmortem.

The situation here is made up: a weekly update that kept coming back in the wrong layout, picked up from the template-drift theme in `fixtures/usage-story/sample-story.md`. It carries no counts, so it has no number ledger.

**What's in it**
- `sample-postmortem.md` — the postmortem, with the headings the workflow's Postmortem section requires

**Check** (from the kit root):
```
python3 scripts/usage_story.py check-postmortem --root fixtures/postmortem sample-postmortem.md
python3 scripts/check_kit_generic.py fixtures/postmortem/README.md fixtures/postmortem/sample-postmortem.md
```

A live postmortem names the PM's own work, people, and sessions. It stays in the live workspace and is never copied here.
