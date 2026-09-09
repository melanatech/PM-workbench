# Formatted document templates (Word/Excel; PowerPoint with caveats)

The pattern: the template owns ALL formatting; Claude supplies only structured content.
Design once in the real app, tag it, drop it here. Never ask Claude to reproduce branding.

## Word (.docx) — the strong path, via docxtpl
1. Design the document in Word exactly as it should look — headers, footers, branding, tables.
2. Replace variable content with Jinja2 tags: {{ quarter }}, {{ revenue }},
   {% for risk in risks %}{{ risk }}{% endfor %} (tags go inside the styled text,
   so they inherit its formatting).
3. Save here as e.g. `leadership-onepager.docx`.
4. Any command producing that deliverable generates the context JSON and runs
   `python3 scripts/render_template.py <template> <context.json> <output.docx>`.
One-time: `pip install --user docxtpl`

## Excel (.xlsx) — pre-formatted workbook + named cells
Don't Jinja-template Excel. Format the workbook once, define named cells/ranges for
the variable values, save it here. The render script writes values into the named
cells via openpyxl; all surrounding formatting survives.

## PowerPoint (.pptx) — the honest caveat
python-pptx placeholder-filling handles text-and-simple-charts decks. For anything
design-heavy, the reliable flow is: Claude drafts per-slide content as text, you
paste into the branded deck. Don't fight the weak leg on a deadline.

## Fallback (always available)
No template yet for a deliverable? The command produces clean markdown/text instead
and logs the missing template in BACKLOG.md. Templates are accelerators, never gates.
