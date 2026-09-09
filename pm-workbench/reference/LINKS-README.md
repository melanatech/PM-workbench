# reference/links.csv — the link library

Not everything needs to be downloaded and processed. If a source system can read
a link live, log the link instead of duplicating the content locally — it's less
work AND it can't go stale the way a saved copy can.

**Why this matters here specifically:** your internal chat tool can already read
Confluence/Jira links directly, and Copilot can read SharePoint links directly.
That means for a lot of "durable context" — templates, policy docs, recurring
dashboards, a strategy deck, a team wiki hub — the fastest and most current path
is: log the link once, and any command that needs it fetches live through the
tool that already knows how to read it.

## Categories
- `template` — a canonical Confluence/SharePoint template (PRD format, launch
  checklist) — reference instead of copying into `reference/templates/`
- `reference-doc` — a policy, glossary, or standing doc you'll point to repeatedly
- `dashboard` — a QuickSight/FullStory/experiment-tool view (pairs with the
  `source_url` in a metric YAML, but useful to log here too if referenced elsewhere)
- `recording` — a Teams meeting recording/transcript link, if kept online rather
  than downloaded
- `other`

## When to still save a full copy instead
- The source will disappear or move (a one-off Slack thread, a version about to
  be overwritten)
- You want a permanent offline copy of something that matters even if the link breaks
- It's genuinely raw material to process (a transcript going through
  `/meeting-closeout`, evidence going into the register) — links.csv is for
  durable REFERENCE material, not working inputs

## Example rows
```
link_id,name,category,url,source_system,what_it_is,last_verified,notes
L001,PRD Template,template,https://yourcompany.atlassian.net/wiki/.../PRD+Template,confluence,Our team's canonical PRD structure,2026-07-20,used by /prd-package
L002,Launch Checklist,template,https://yourcompany.sharepoint.com/.../launch-checklist.docx,sharepoint,Standard launch checklist,2026-07-20,fetch via Copilot when needed
L003,Team Wiki Home,reference-doc,https://yourcompany.atlassian.net/wiki/.../Home,confluence,Jump-off point for team docs,2026-07-20,
```
