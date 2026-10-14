# Formatted document templates (Word/Excel; PowerPoint with caveats)

The pattern: the template owns ALL formatting; Claude supplies only structured content.
Design once in the real app, tag it, drop it here. Never ask Claude to reproduce branding.

## Word (.docx) — stdlib WordprocessingML
`scripts/render_template.py` writes headings, paragraphs, bullets, tables, and
links with the standard library (no pandoc, no python-docx). Branding stays in
the template: drop a company `.docx` here and the renderer copies its
`word/styles.xml` into the result.

```bash
python3 scripts/render_template.py reference/templates/formatted/brand.docx context.json output.docx
```

`context.json` supplies `markdown` (and an optional `title`). Audience-facing
drafts go through `scripts/publish.py`, which calls this renderer.

## HTML — one self-contained page
`page.html` is the shell (inline CSS, `{{title}}` and `{{content}}`).
`scripts/publish.py` fills it for the `html` format. No external stylesheet.

## Excel (.xlsx) and PowerPoint (.pptx)
Not rendered. `scripts/render_template.py` exits with a message for those
suffixes, and the caller keeps the markdown draft.

## Fallback (always available)
No template yet for a deliverable? The command produces clean markdown/text instead
and logs the missing template in BACKLOG.md. Templates are accelerators, never gates.
